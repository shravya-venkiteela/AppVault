from appvault.parser import parse_email, ParsedStatus

REJECTION_SAMPLE = """
Dear Candidate,
Thank you for your interest in the Deloitte - Data & AI Solutions Engineering Analyst position.
Unfortunately, after careful consideration, we have determined that our current position is not ideally suited to your talents, experience, and qualifications.
We encourage you to regularly visit the Deloitte Careers website to review positions that become available.
Thank you,
Deloitte Recruiting
"""

CONFIRMATION_SENDER_ONLY_SAMPLE = """
Hi Candidate,
Thanks for your interest in iSpot! We've received your application for Data Scientist, and we're delighted that you would consider joining our team.
We'll review your application and be in touch if your qualifications match our needs for the role.
Thank you,
iSpot Recruiting Team
"""

CONFIRMATION_WITH_REQID_SAMPLE = """
Hello Candidate,
Thank you for your interest in joining Lumen! We have received your application for the Lead Monetization Analyst position (100000) and appreciate the time you invested in applying for a position with us.
Please read below on what to expect next in the recruitment process.
Best Regards,
Lumen Technologies Talent Acquisition
"""

ASSESSMENT_NO_ROLE_SAMPLE = """
Hello,
Thanks for completing [Acme Corp | Acme Corp Securities] Software Engineering Campus Assessment. We've sent your submission to Acme Corp.
In the meantime, you can go ahead and solve more of such code challenges.
Thanks,
HackerRank Team
"""

OFFER_NO_ROLE_SAMPLE = """
Hi Candidate,
Great news! You aced it. We'd love you to join us at Globex.
We know what a big step this is, so if there's anything you still need to know, please contact us at any time.
Here is how you can review your offer:
Step 1: You'll find your job offer on your candidate home page.
Looking forward to hearing from you,
Globex Recruitment Team
Reference CID: C00000000
"""

MARKETING_BLAST_NEGATIVE_SAMPLE = """
Get ready to kick-start your Globex career journey!
Looking to build a career driven by learning and fueled by an inclusive culture? Grab this unique opportunity to jumpstart your career with us.
We request every candidate to visit here to learn more about Assessment and General guidelines for our hiring process.
Register now and submit your details by 31-July-2023 11:59 PM to begin your career journey at Globex!
Good luck!
"""


def test_rejection_extracts_company_and_role():
    result = parse_email(REJECTION_SAMPLE)
    assert result is not None, "Expected a match, got None"
    assert result.status == ParsedStatus.REJECTED
    assert "Deloitte" in result.company
    assert "Data & AI Solutions Engineering Analyst" in result.role


def test_confirmation_falls_back_to_sender_for_company():
    result = parse_email(
        CONFIRMATION_SENDER_ONLY_SAMPLE,
        sender_display_name="iSpot Recruiting Team",
    )
    assert result is not None, "Expected a match, got None"
    assert result.status == ParsedStatus.PENDING
    assert result.company == "iSpot"
    assert result.role == "Data Scientist"


def test_confirmation_strips_trailing_req_id_from_role():
    result = parse_email(CONFIRMATION_WITH_REQID_SAMPLE)
    assert result is not None, "Expected a match, got None"
    assert result.status == ParsedStatus.PENDING
    assert "Lumen" in result.company
    assert result.role == "Lead Monetization Analyst"
    assert "100000" not in result.role, "req id leaked into role string"


def test_assessment_email_returns_none_due_to_missing_role():
    result = parse_email(
        ASSESSMENT_NO_ROLE_SAMPLE,
        sender_display_name="HackerRank Team",
    )
    assert result is None, (
        "Assessment emails have no extractable role and MUST return None"
    )


def test_offer_email_returns_none_due_to_missing_role():
    result = parse_email(
        OFFER_NO_ROLE_SAMPLE,
        sender_display_name="Globex Recruitment Team",
    )
    assert result is None, (
        "Offer emails have no extractable role and MUST return None"
    )


def test_marketing_blast_is_a_true_negative():
    result = parse_email(
        MARKETING_BLAST_NEGATIVE_SAMPLE,
        sender_display_name="Globex Recruitment Team",
    )
    assert result is None, (
        "Generic marketing/recruiting-blast emails must not be logged"
    )


def test_generic_word_is_rejected_as_company():
    text = "Thanks for applying! We look forward to having you join us at our growing team."
    result = parse_email(text)
    if result is not None:
        assert result.company.lower() not in {"us", "our", "the", "you", "your"}


def test_lowercase_starting_role_is_extracted():
    text = (
        "Thank you for your interest in joining Acme! "
        "We have received your application for iOS Developer, thanks."
    )
    result = parse_email(text)
    assert result is not None
    assert result.company == "Acme"
    assert result.role == "iOS Developer"

    
if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")