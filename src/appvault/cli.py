import click
from datetime import date, datetime

from appvault.exceptions import StorageError
from appvault.models import Application, ApplicationStatus
from appvault.storage import ApplicationStore


@click.group()
@click.option("--storage-path", type=click.Path(), default=None)
@click.pass_context
def cli(ctx, storage_path):
    """Command-line interface for managing job applications."""
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
    