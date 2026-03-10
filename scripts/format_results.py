"""
Result formatting utilities for USPTO API responses.

Converts raw JSON API responses into human-readable text summaries,
tables, and exportable formats (CSV, JSON).

These formatters are designed to be called by Claude when presenting
results to the user. They extract the most relevant fields and present
them in a scannable format.
"""

import json
import csv
import io
from typing import Optional


def format_patent_list(response: dict, source: str = "patentsview") -> str:
    """Format a list of patents into a readable summary.

    Args:
        response: Raw API response from PatentsView or ODP
        source: 'patentsview' or 'odp' to determine field names

    Returns:
        Formatted text summary
    """
    lines = []

    if source == "patentsview":
        patents = response.get("patents", [])
        total = response.get("total_hits", len(patents))
        count = response.get("count", len(patents))

        lines.append(f"Found {total:,} patents (showing {count}):\n")

        for i, p in enumerate(patents, 1):
            pat_id = p.get("patent_id", "N/A")
            title = p.get("patent_title", "No title")
            date = p.get("patent_date", "N/A")
            cited = p.get("patent_num_times_cited_by_us_patents", 0)

            lines.append(f"  {i}. US {pat_id} — {title}")
            lines.append(f"     Granted: {date} | Cited by: {cited} patents")

            # Assignee info — check nested array first, then flat field
            assignees = p.get("assignees", [])
            if assignees:
                assignee = assignees[0].get("assignee_organization", "")
            else:
                assignee = p.get("assignee_organization")
            if assignee:
                lines.append(f"     Assignee: {assignee}")

            # Inventor info — check nested array first, then flat fields
            inventors = p.get("inventors", [])
            if inventors:
                inv_first = inventors[0].get("inventor_name_first", "")
                inv_last = inventors[0].get("inventor_name_last", "")
            else:
                inv_first = p.get("inventor_name_first")
                inv_last = p.get("inventor_name_last")
            if inv_first and inv_last:
                lines.append(f"     Inventor: {inv_first} {inv_last}")

            lines.append("")

    elif source == "odp":
        # Handle both old format (results[]) and new format (patentFileWrapperDataBag[])
        results = response.get("patentFileWrapperDataBag",
                    response.get("results",
                    response if isinstance(response, list) else []))
        total = response.get("count",
                    response.get("totalCount", len(results))) if isinstance(response, dict) else len(results)

        lines.append(f"Found {total} applications:\n")

        for i, app in enumerate(results, 1):
            app_num = app.get("applicationNumberText", "N/A")
            meta = app.get("applicationMetaData", {})
            title = meta.get("inventionTitle", app.get("inventionTitle", "No title"))
            status = meta.get("applicationStatusDescriptionText",
                        app.get("appStatus", "Unknown"))
            filing_date = meta.get("filingDate", app.get("filingDate", "N/A"))
            patent_num = meta.get("patentNumber", app.get("patentNumber", ""))

            lines.append(f"  {i}. App {app_num} — {title}")
            line = f"     Filed: {filing_date} | Status: {status}"
            if patent_num:
                line += f" | Patent: US {patent_num}"
            lines.append(line)

            # Show assignee from assignment records if available
            assignments = app.get("assignmentBag", [])
            if assignments:
                # Use the most recent assignment's assignee
                latest = assignments[0]
                assignee_bag = latest.get("assigneeBag", [])
                if assignee_bag:
                    assignee_name = assignee_bag[0].get("assigneeNameText", "")
                    if assignee_name:
                        lines.append(f"     Assignee: {assignee_name}")

            lines.append("")

    return "\n".join(lines)


def format_patent_detail(patent: dict, source: str = "patentsview") -> str:
    """Format detailed information about a single patent.

    Args:
        patent: Single patent record
        source: 'patentsview' or 'odp'

    Returns:
        Detailed formatted summary
    """
    lines = []

    if source == "patentsview":
        # Handle response wrapper
        if "patents" in patent:
            patents = patent["patents"]
            if not patents:
                return "No patent found."
            patent = patents[0]

        lines.append(f"US Patent {patent.get('patent_id', 'N/A')}")
        lines.append(f"{'=' * 50}")
        lines.append(f"Title:    {patent.get('patent_title', 'N/A')}")
        lines.append(f"Granted:  {patent.get('patent_date', 'N/A')}")
        lines.append(f"Type:     {patent.get('patent_type', 'N/A')}")
        abstract = patent.get('patent_abstract', 'N/A') or 'N/A'
        if len(abstract) > 300:
            truncated = abstract[:300].rsplit(' ', 1)[0]
            abstract = truncated + "..."
        lines.append(f"Abstract: {abstract}")
        lines.append(f"")

        # Assignee — nested array
        assignees = patent.get("assignees", [])
        if assignees:
            assignee_names = [a.get("assignee_organization", "Unknown")
                              for a in assignees if a.get("assignee_organization")]
            if assignee_names:
                lines.append(f"Assignee:           {', '.join(assignee_names)}")

        # Inventors — nested array
        inventors = patent.get("inventors", [])
        if inventors:
            inv_names = [f"{inv.get('inventor_name_first', '')} {inv.get('inventor_name_last', '')}".strip()
                         for inv in inventors[:5]]
            if inv_names:
                inv_str = ", ".join(inv_names)
                if len(inventors) > 5:
                    inv_str += f" (+{len(inventors) - 5} more)"
                lines.append(f"Inventors:          {inv_str}")

        # CPC — nested array
        cpc_current = patent.get("cpc_current", [])
        if cpc_current:
            cpc_codes = list(set(c.get("cpc_subclass_id", c.get("cpc_group_id", ""))
                                 for c in cpc_current[:5]))
            if cpc_codes:
                lines.append(f"CPC:                {', '.join(cpc_codes)}")

        lines.append(f"")
        lines.append(f"Citations made:     {patent.get('patent_num_us_patents_cited', 'N/A')}")
        lines.append(f"Times cited by:     {patent.get('patent_num_times_cited_by_us_patents', 'N/A')}")
        lines.append(f"Processing days:    {patent.get('patent_processing_days', 'N/A')}")

    return "\n".join(lines)


def format_citation_list(response: dict, direction: str = "forward") -> str:
    """Format patent citation data.

    Args:
        response: Citation API response
        direction: 'forward' (patents this one cites) or 'backward'/'cited_by' (patents citing this one)

    Returns:
        Formatted citation list
    """
    citations = response.get("us_patent_citations", [])
    total = response.get("total_hits", len(citations))

    if direction == "forward":
        label = "Patents cited by this patent"
    else:  # "backward" or "cited_by"
        label = "Patents that cite this patent"

    lines = [f"{label} ({total} total):\n"]

    for i, c in enumerate(citations, 1):
        citing = c.get("patent_id", "N/A")
        cited = c.get("citation_patent_id", "N/A")
        category = c.get("citation_category", "")
        date = c.get("citation_date", "")

        if direction == "forward":
            lines.append(f"  {i}. US {cited} ({category}) — {date}")
        else:
            lines.append(f"  {i}. Cited by US {citing} — {date}")

    return "\n".join(lines)


def format_ptab_results(response: dict) -> str:
    """Format PTAB proceeding search results.

    Handles both old format (results[]) and ODP format (patentTrialProceedingDataBag[]).

    Args:
        response: PTAB API response

    Returns:
        Formatted PTAB proceedings list
    """
    if isinstance(response, list):
        proceedings = response
    elif isinstance(response, dict):
        proceedings = (response.get("patentTrialProceedingDataBag", [])
                       or response.get("results", []))
    else:
        proceedings = []

    total = response.get("count", response.get("totalCount", len(proceedings))) if isinstance(response, dict) else len(proceedings)

    lines = [f"PTAB Proceedings ({total} found):\n"]

    for i, p in enumerate(proceedings, 1):
        trial_num = p.get("trialNumber", "N/A")

        # Handle nested ODP format
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


def format_assignment_results(response: dict) -> str:
    """Format patent assignment search results.

    Handles both old format (results[]) and ODP format (patentFileWrapperDataBag[]).

    Args:
        response: Assignment API response

    Returns:
        Formatted assignment list showing ownership chain
    """
    # Extract assignments from various response formats
    assignments = []

    if isinstance(response, list):
        assignments = response
    elif isinstance(response, dict):
        # ODP format: patentFileWrapperDataBag[].assignmentBag[]
        bags = response.get("patentFileWrapperDataBag", [])
        if bags:
            app_num = ""
            for bag in bags:
                app_num = bag.get("applicationNumberText", app_num)
                for a in bag.get("assignmentBag", []):
                    a["_applicationNumber"] = app_num
                    assignments.append(a)
        # Direct assignments list (from company/recent search)
        elif "assignments" in response:
            assignments = response["assignments"]
        # Old format fallback
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
        # ODP format fields
        reel_frame = a.get("reelAndFrameNumber", a.get("reelFrame", "N/A"))
        recorded = a.get("assignmentRecordedDate", a.get("recordedDate", "N/A"))
        conveyance = a.get("conveyanceText", "N/A")

        # ODP nested assignor/assignee bags
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
        response: Rejection API response

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
        # Clean datetime format to date only
        if action_date and "T" in str(action_date):
            action_date = str(action_date).split("T")[0]
        art_unit = r.get("groupArtUnitNumber", "")

        # Build rejection type string
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


if __name__ == "__main__":
    # Quick test with sample data
    sample = {
        "patents": [
            {
                "patent_id": "10000000",
                "patent_title": "Coherent LADAR using intra-pixel quadrature detection",
                "patent_date": "2018-06-19",
                "patent_num_times_cited_by_us_patents": 42,
            }
        ],
        "count": 1,
        "total_hits": 1,
    }
    print(format_patent_list(sample))
