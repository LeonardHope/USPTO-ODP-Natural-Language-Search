"""
Result formatting utilities for USPTO ODP API responses.

Converts raw JSON API responses into human-readable text summaries,
tables, and exportable formats (CSV, JSON).

These formatters are designed to be called by Claude when presenting
results to the user. They extract the most relevant fields and present
them in a scannable format.
"""

import json
import csv
import io


def format_patent_list(response: dict, source: str = "odp") -> str:
    """Format a list of patent applications into a readable summary.

    Args:
        response: Raw API response from ODP patent search
        source: Always 'odp' (kept for API compatibility)

    Returns:
        Formatted text summary
    """
    if isinstance(response, dict) and response.get("error"):
        return str(response["error"])

    results = response.get("patentFileWrapperDataBag",
                response.get("results",
                response if isinstance(response, list) else []))
    total = response.get("count",
                response.get("totalCount", len(results))) if isinstance(response, dict) else len(results)

    lines = [f"Found {total} applications:\n"]

    for i, app in enumerate(results, 1):
        app_num = app.get("applicationNumberText", "N/A")
        meta = app.get("applicationMetaData", {})
        title = meta.get("inventionTitle", app.get("inventionTitle", "No title"))
        status = meta.get("applicationStatusDescriptionText",
                    app.get("appStatus", "Unknown"))
        filing_date = meta.get("filingDate", app.get("filingDate", "N/A"))
        patent_num = meta.get("patentNumber", app.get("patentNumber", ""))
        grant_date = meta.get("grantDate", "")

        lines.append(f"  {i}. App {app_num} — {title}")
        line = f"     Filed: {filing_date} | Status: {status}"
        if patent_num:
            line += f" | Patent: US {patent_num}"
        if grant_date:
            line += f" | Granted: {grant_date}"
        lines.append(line)

        # Show assignee from assignment records if available
        assignments = app.get("assignmentBag", [])
        if assignments:
            latest = assignments[0]
            assignee_bag = latest.get("assigneeBag", [])
            if assignee_bag:
                assignee_name = assignee_bag[0].get("assigneeNameText", "")
                if assignee_name:
                    lines.append(f"     Assignee: {assignee_name}")

        # Show applicant from metadata
        applicants = meta.get("applicantBag", [])
        if applicants and not assignments:
            names = [a.get("applicantNameText", "") for a in applicants if a.get("applicantNameText")]
            if names:
                lines.append(f"     Applicant: {', '.join(names)}")

        # Show CPC if available
        cpc = meta.get("cpcClassificationBag", [])
        if cpc:
            cpc_codes = list(set(str(c) for c in cpc[:3]))
            if cpc_codes:
                lines.append(f"     CPC: {', '.join(cpc_codes)}")

        lines.append("")

    return "\n".join(lines)


def format_patent_detail(patent: dict, source: str = "odp") -> str:
    """Format detailed information about a single patent application.

    Args:
        patent: Single application record or response wrapper
        source: Always 'odp' (kept for API compatibility)

    Returns:
        Detailed formatted summary
    """
    if isinstance(patent, dict) and patent.get("error"):
        return str(patent["error"])

    # Unwrap response envelope if needed
    if "patentFileWrapperDataBag" in patent:
        bags = patent["patentFileWrapperDataBag"]
        if not bags:
            return "No patent found."
        patent = bags[0]

    meta = patent.get("applicationMetaData", {})
    app_num = patent.get("applicationNumberText", "N/A")
    patent_num = meta.get("patentNumber", "")
    title = meta.get("inventionTitle", "N/A")
    status = meta.get("applicationStatusDescriptionText", "N/A")
    filing_date = meta.get("filingDate", "N/A")
    grant_date = meta.get("grantDate", "N/A")
    app_type = meta.get("applicationTypeCategory",
                  meta.get("applicationTypeLabelName", "N/A"))
    examiner = meta.get("examinerNameText", "")
    art_unit = meta.get("groupArtUnitNumber", "")

    header = f"US Patent {patent_num}" if patent_num else f"Application {app_num}"
    lines = [header, "=" * 50]
    lines.append(f"Title:    {title}")
    lines.append(f"Status:   {status}")
    lines.append(f"Filed:    {filing_date}")
    if patent_num:
        lines.append(f"Granted:  {grant_date}")
        lines.append(f"Patent:   US {patent_num}")
    lines.append(f"App No:   {app_num}")
    lines.append(f"Type:     {app_type}")
    if examiner:
        lines.append(f"Examiner: {examiner}")
    if art_unit:
        lines.append(f"Art Unit: {art_unit}")

    # Applicant info
    applicants = meta.get("applicantBag", [])
    if applicants:
        names = [a.get("applicantNameText", "") for a in applicants if a.get("applicantNameText")]
        if names:
            lines.append(f"")
            lines.append(f"Applicant:          {', '.join(names)}")

    # Inventor info
    inventors = meta.get("inventorBag", [])
    if inventors:
        inv_names = [inv.get("inventorNameText", "").strip() for inv in inventors[:5]]
        inv_names = [n for n in inv_names if n]
        if inv_names:
            inv_str = ", ".join(inv_names)
            if len(inventors) > 5:
                inv_str += f" (+{len(inventors) - 5} more)"
            lines.append(f"Inventors:          {inv_str}")

    # CPC classifications
    cpc = meta.get("cpcClassificationBag", [])
    if cpc:
        cpc_codes = list(set(str(c) for c in cpc[:5]))
        if cpc_codes:
            lines.append(f"CPC:                {', '.join(cpc_codes)}")

    return "\n".join(lines)


def format_ptab_results(response: dict) -> str:
    """Format PTAB trial, appeal, or interference search results.

    Handles multiple response bag types from the various PTAB endpoints.

    Args:
        response: PTAB API response

    Returns:
        Formatted PTAB results list
    """
    if isinstance(response, list):
        items = response
        response = {}
    elif isinstance(response, dict):
        # Detect which type of result we're formatting
        if "patentAppealDataBag" in response:
            return _format_appeal_results(response)
        items = (response.get("patentTrialProceedingDataBag", [])
                 or response.get("patentTrialDecisionDataBag", [])
                 or response.get("patentTrialDocumentDataBag", [])
                 or response.get("results", []))
    else:
        items = []

    total = response.get("count", response.get("totalCount", len(items))) if isinstance(response, dict) else len(items)

    lines = [f"PTAB Results ({total} found):\n"]

    for i, p in enumerate(items, 1):
        trial_num = p.get("trialNumber", p.get("interferenceNumber", "N/A"))

        trial_meta = p.get("trialMetaData", {})
        patent_data = p.get("patentOwnerData", {})
        petitioner_data = p.get("regularPetitionerData", {})

        proc_type = trial_meta.get("trialTypeCode", p.get("proceedingTypeCategory", "N/A"))
        status = trial_meta.get("trialStatusCategory", p.get("proceedingStatus", "N/A"))
        patent_num = patent_data.get("patentNumber", p.get("patentNumber", "N/A"))
        filing_date = trial_meta.get("petitionFilingDate", p.get("filingDate", "N/A"))
        petitioner = petitioner_data.get("realPartyInInterestName", p.get("petitionerPartyName", "N/A"))
        patent_owner = patent_data.get("inventorName", p.get("patentOwnerPartyName", "N/A"))

        lines.append(f"  {i}. {trial_num} ({proc_type})")
        lines.append(f"     Patent: US {patent_num} | Status: {status}")
        lines.append(f"     Filed: {filing_date}")
        lines.append(f"     Petitioner: {petitioner}")
        lines.append(f"     Patent Owner: {patent_owner}")
        lines.append("")

    return "\n".join(lines)


def _format_appeal_results(response: dict) -> str:
    """Format PTAB appeal decision results.

    Appeals use a different response structure than trial proceedings:
    appealNumber, appealMetaData, appellantData, decisionData.
    """
    appeals = response.get("patentAppealDataBag", [])
    total = response.get("count", len(appeals))

    lines = [f"PTAB Appeal Decisions ({total} found):\n"]

    for i, a in enumerate(appeals, 1):
        appeal_num = a.get("appealNumber", "N/A")
        meta = a.get("appealMetaData", {})
        appellant = a.get("appellantData", {})
        decision = a.get("decisionData", {})
        doc = a.get("documentData", {})

        filing_date = meta.get("appealFilingDate", "N/A")
        app_type = meta.get("applicationTypeCategory", "N/A")
        app_num = appellant.get("applicationNumberText", "N/A")
        art_unit = appellant.get("groupArtUnitNumber", "")
        tech_center = appellant.get("technologyCenterNumber", "")
        party = appellant.get("realPartyInInterestName", "N/A")
        counsel = appellant.get("counselName", "")
        outcome = decision.get("appealOutcomeCategory", "N/A")
        decision_date = decision.get("decisionIssueDate", doc.get("documentFilingDate", "N/A"))

        lines.append(f"  {i}. Appeal {appeal_num} ({app_type})")
        lines.append(f"     App: {app_num} | Art Unit: {art_unit} | TC: {tech_center}")
        lines.append(f"     Filed: {filing_date} | Decided: {decision_date}")
        lines.append(f"     Outcome: {outcome}")
        lines.append(f"     Party: {party}")
        if counsel:
            lines.append(f"     Counsel: {counsel}")
        lines.append("")

    return "\n".join(lines)


def format_assignment_results(response: dict) -> str:
    """Format patent assignment search results.

    Args:
        response: Assignment API response

    Returns:
        Formatted assignment list showing ownership chain
    """
    assignments = []

    if isinstance(response, list):
        assignments = response
    elif isinstance(response, dict):
        bags = response.get("patentFileWrapperDataBag", [])
        if bags:
            app_num = ""
            for bag in bags:
                app_num = bag.get("applicationNumberText", app_num)
                for a in bag.get("assignmentBag", []):
                    a["_applicationNumber"] = app_num
                    assignments.append(a)
        elif "assignments" in response:
            assignments = response["assignments"]
        else:
            assignments = response.get("results", [])

    total = len(assignments)
    if isinstance(response, dict):
        total = response.get("count", response.get("totalCount", total))

    lines = [f"Patent Assignments ({total} found):\n"]

    if not assignments:
        error = response.get("error", "") if isinstance(response, dict) else ""
        if error:
            lines.append(f"  {error}")
        return "\n".join(lines)

    for i, a in enumerate(assignments, 1):
        reel_frame = a.get("reelAndFrameNumber", a.get("reelFrame", "N/A"))
        recorded = a.get("assignmentRecordedDate", a.get("recordedDate", "N/A"))
        conveyance = a.get("conveyanceText", "N/A")

        assignor_bag = a.get("assignorBag", [])
        assignee_bag = a.get("assigneeBag", [])
        assignor = assignor_bag[0].get("assignorName", "N/A") if assignor_bag else a.get("assignorName", "N/A")
        assignee = assignee_bag[0].get("assigneeNameText", "N/A") if assignee_bag else a.get("assigneeName", "N/A")

        app_num = a.get("_applicationNumber", a.get("applicationNumber", ""))
        patent_num = a.get("patentNumber", "")

        lines.append(f"  {i}. Reel/Frame: {reel_frame} — Recorded: {recorded}")
        lines.append(f"     From: {assignor}")
        lines.append(f"     To:   {assignee}")
        lines.append(f"     Type: {conveyance}")
        if patent_num:
            lines.append(f"     Ref:  Patent US {patent_num}")
        elif app_num:
            lines.append(f"     Ref:  App {app_num}")
        lines.append("")

    return "\n".join(lines)


def format_rejection_results(response: dict) -> str:
    """Format office action rejection results.

    Args:
        response: Rejection API response (DSAPI format)

    Returns:
        Formatted rejection summary
    """
    records = response.get("response", {}).get("docs", [])
    total = response.get("response", {}).get("numFound", len(records))

    lines = [f"Office Action Rejections ({total} found):\n"]

    for i, r in enumerate(records, 1):
        app_id = r.get("patentApplicationNumber", "N/A")
        action_type = r.get("actionTypeCategory", "")
        doc_code = r.get("legacyDocumentCodeIdentifier", "")
        action_date = r.get("submissionDate", "N/A")
        if action_date and "T" in str(action_date):
            action_date = str(action_date).split("T")[0]
        art_unit = r.get("groupArtUnitNumber", "")

        rej_types = []
        if r.get("hasRej101") or r.get("aliceIndicator") or r.get("mayoIndicator"):
            rej_types.append("101")
        if r.get("hasRej102"):
            rej_types.append("102")
        if r.get("hasRej103"):
            rej_types.append("103")
        if r.get("hasRej112"):
            rej_types.append("112")
        if r.get("hasRejDP"):
            rej_types.append("DP")

        rej_str = ", ".join(rej_types) if rej_types else "Other"
        type_label = doc_code or action_type or "N/A"

        lines.append(f"  {i}. App {app_id} — {type_label} ({action_date})")
        lines.append(f"     Rejection basis: {rej_str}")
        if art_unit:
            lines.append(f"     Art Unit: {art_unit}")
        lines.append("")

    return "\n".join(lines)


def format_petition_results(response: dict) -> str:
    """Format petition decision results.

    Args:
        response: Petition Decisions API response

    Returns:
        Formatted petition decisions list
    """
    decisions = response.get("petitionDecisionDataBag", [])
    total = response.get("count", len(decisions))

    lines = [f"Petition Decisions ({total} found):\n"]

    for i, d in enumerate(decisions, 1):
        app_num = d.get("applicationNumberText", "N/A")
        decision_date = d.get("decisionDate", "N/A")
        decision = d.get("decisionTypeCodeDescriptionText", d.get("decisionTypeCode", "N/A"))
        title = d.get("inventionTitle", "")
        art_unit = d.get("groupArtUnitNumber", "")
        tech_center = d.get("technologyCenter", "")
        office = d.get("finalDecidingOfficeName", "")
        issues = d.get("petitionIssueConsideredTextBag", [])
        rules = d.get("ruleBag", [])

        lines.append(f"  {i}. App {app_num} — {decision} ({decision_date})")
        if title:
            lines.append(f"     Title: {title[:80]}")
        if issues:
            lines.append(f"     Issue: {', '.join(issues[:2])}")
        if rules:
            lines.append(f"     Rules: {', '.join(rules[:3])}")
        if office:
            lines.append(f"     Office: {office}")
        if art_unit or tech_center:
            lines.append(f"     Art Unit: {art_unit} | TC: {tech_center}")
        lines.append("")

    return "\n".join(lines)


def to_csv(records: list, fields: list = None) -> str:
    """Convert a list of records to CSV format.

    Args:
        records: List of dict records
        fields: Specific fields to include (default: all)

    Returns:
        CSV string
    """
    if not records:
        return "No records to export."

    if fields is None:
        fields = list(records[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record)

    return output.getvalue()


def to_json(records: list, pretty: bool = True) -> str:
    """Convert records to JSON string.

    Args:
        records: List of dict records
        pretty: Pretty-print with indentation

    Returns:
        JSON string
    """
    return json.dumps(records, indent=2 if pretty else None)
