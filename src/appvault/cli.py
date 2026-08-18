import click
import logging
from datetime import date, datetime

from appvault.exceptions import AppVaultError, StorageError
from appvault.models import Application, ApplicationStatus
from appvault.storage import ApplicationStore
from appvault.duplicates import find_duplicates
from appvault.config import load_email_credentials
from appvault.email_client import EmailClient
from appvault.parser import parse_email, ParsedStatus
from appvault.scoring import score_applications
from appvault.logging_setup import setup_logging

logger = logging.getLogger("appvault")


@click.group()
@click.option("--storage-path", type=click.Path(), default=None)
@click.option("--debug", is_flag=True, default=False, help="Enable verbose debug logging.")
@click.pass_context
def cli(ctx, storage_path, debug):
    """Command-line interface for managing job applications."""
    setup_logging(debug=debug)
    ctx.ensure_object(dict)
    ctx.obj["store"] = ApplicationStore(storage_path)


@cli.command()
@click.option("--company", required=True)
@click.option("--role", required=True)
@click.option("--applied-date", default=None, type=click.DateTime(formats=["%Y-%m-%d"]), help="Date in YYYY-MM-DD format")
@click.option("--interest", type=int, default=None)
@click.pass_context
def add(ctx, company, role, applied_date, interest):
    """Add a new job application."""
    store = ctx.obj["store"]
    dupes = find_duplicates(company, store.load_all())
    if dupes:
        best, score = dupes[0]
        click.echo(f"Warning: '{company}' looks similar to existing  '{best.company}' - (similarity {score:.2f}, id = {best.application_id}). Adding anyway.")

    applied = applied_date.date() if applied_date else date.today()
    application = Application(
        company=company,
        role=role,
        applied_date=applied,
        interest_rating=interest,
    )
    store.add(application)
    click.echo(f"Added application for {company} - {role}")


@cli.command(name="list")
@click.pass_context
def list_applications(ctx):
    """List all job applications."""
    store = ctx.obj["store"]
    applications = store.load_all()
    if not applications:
        click.echo("No applications found.")
        return
    for app in applications:
        click.echo(f"[{app.application_id}] {app.company} - {app.role} - {app.status.value} - Applied on: {app.applied_date}")


@cli.group()
def status():
    """Commands to update the status of applications."""
    pass


@status.command(name="set")
@click.argument("application_id")
@click.argument("new_status", type=click.Choice([status.value for status in ApplicationStatus]))
@click.pass_context
def set_status(ctx, application_id, new_status):
    """Set the status of a job application."""
    store = ctx.obj["store"]
    try:
        application = store.update_status(application_id, ApplicationStatus(new_status))
    except StorageError as e:
        click.echo(f"Error: {e}")
        return
    click.echo(f"Updated application [{application.company} - {application.role}] to {new_status}")


_STATUS_MAP = {
    ParsedStatus.PENDING: ApplicationStatus.PENDING,
    ParsedStatus.INTERVIEW: ApplicationStatus.INTERVIEW,
    ParsedStatus.REJECTED: ApplicationStatus.REJECTED,
    ParsedStatus.OFFER: ApplicationStatus.OFFER,
}


@cli.command()
@click.option("--limit", default=20, help="Number of recent emails to fetch")
@click.option("--folder", default="INBOX", help="IMAP folder to scan.")
@click.pass_context
def sync(ctx, limit, folder):
    """Scan recent emails and log new applications found in them."""
    store = ctx.obj["store"]

    try:
        creds = load_email_credentials()
    except AppVaultError as e:
        click.echo(f"Error loading email credentials: {e}")
        return

    created = 0
    skipped_duplicate = 0
    skipped_no_match = 0
    skipped_invalid = 0

    try:
        with EmailClient(creds) as client:
            messages = client.fetch_recent_messages(folder=folder, limit=limit)
    except AppVaultError as e:
        click.echo(f"Error fetching emails: {e}")
        return

    existing_applications = store.load_all()

    for message in messages:
        parsed = parse_email(message.body, sender_display_name=message.sender_display_name)

        if parsed is None:
            click.echo(f"  [no match] Subject: {message.subject!r} From: {message.sender_display_name!r}")
            skipped_no_match += 1
            continue

        click.echo(
            f"  [parsed] company={parsed.company!r} role={parsed.role!r} status={parsed.status.value} "
            f"| subject={message.subject!r} sender={message.sender_display_name!r}"
        )

        mapped_status = _STATUS_MAP.get(parsed.status)
        if mapped_status is None:
            skipped_no_match += 1
            continue

        dupes = find_duplicates(parsed.company, existing_applications, role=parsed.role)
        if dupes:
            best, score = dupes[0]
            click.echo(
                f"Skipping '{parsed.company} - {parsed.role}': "
                f"looks like existing '{best.company}' (similarity {score:.2f})"
            )
            skipped_duplicate += 1
            continue

        try:
            application = Application(
                company=parsed.company,
                role=parsed.role,
                applied_date=date.today(),
                status=mapped_status,
                sender=message.sender_display_name,
                received_at=datetime.now(),
            )
        except ValueError as e:
            click.echo(f"Skipping malformed match from '{message.sender_display_name}': {e}")
            skipped_invalid += 1
            continue

        store.add(application)
        existing_applications.append(application)
        click.echo(f"Logged: {parsed.company} - {parsed.role} ({mapped_status.value})")
        created += 1

    click.echo(
        f"\nSync complete: {created} logged, "
        f"{skipped_duplicate} skipped (duplicate), "
        f"{skipped_no_match} skipped (no confident match), "
        f"{skipped_invalid} skipped (invalid data)"
    )


@cli.command(name="duplicate-check")
@click.argument("company")
@click.option("--role", default=None, help="Optionally check against a specific role too.")
@click.pass_context
def duplicate_check(ctx, company, role):
    """Check if a company name looks similar to an existing application."""
    store = ctx.obj["store"]
    existing = store.load_all()

    dupes = find_duplicates(company, existing, role=role)

    if not dupes:
        click.echo(f"No similar applications found for '{company}'.")
        return

    click.echo(f"Found {len(dupes)} similar application(s):")
    for app, score in dupes:
        role_note = f" - {app.role}" if role else ""
        click.echo(f"  [{app.application_id}] {app.company}{role_note} (similarity {score:.2f})")


@cli.command()
@click.option("--top", default=5, help="Number of top applications to highlight.")
@click.pass_context
def prioritize(ctx, top):
    """Rank applications by follow-up priority and explain the top picks."""
    store = ctx.obj["store"]
    applications = store.load_all()

    if not applications:
        click.echo("No applications found.")
        return

    scored = score_applications(applications)

    if not scored:
        click.echo("No actionable applications to prioritize (all are rejected or withdrawn).")
        return

    click.echo(f"Top {min(top, len(scored))} to follow up on:\n")
    for rank, entry in enumerate(scored[:top], start=1):
        app = entry.application
        click.echo(f"{rank}. {app.company} - {app.role} ({app.status.value}, {entry.total_score:.0f} pts)")
        for reason in entry.reasons:
            click.echo(f"   - {reason}")
        click.echo()

    remaining = scored[top:]
    if remaining:
        click.echo(f"Also tracked ({len(remaining)} more):")
        for entry in remaining:
            app = entry.application
            click.echo(f"   {app.company} - {app.role} ({app.status.value}, {entry.total_score:.0f} pts)")


@cli.command()
@click.argument("application_id")
@click.pass_context
def delete(ctx, application_id):
    """Delete an application by ID."""
    store = ctx.obj["store"]
    try:
        removed = store.delete(application_id)
    except StorageError as e:
        click.echo(f"Error: {e}")
        return
    click.echo(f"Deleted [{removed.application_id}] {removed.company} - {removed.role}")


@status.command(name="rate")
@click.argument("application_id")
@click.argument("rating", type=click.IntRange(1, 5))
@click.pass_context
def rate_application(ctx, application_id, rating):
    """Set the interest rating (1-5) for an application."""
    store = ctx.obj["store"]
    apps = store.load_all()
    for app in apps:
        if app.application_id == application_id:
            app.interest_rating = rating
            store.save_all(apps)
            click.echo(f"Set interest rating for {app.company} - {app.role} to {rating}/5")
            return
    click.echo(f"Error: No application found with id {application_id}")