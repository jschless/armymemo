from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .document import BodyItem, MemoDocument, Recipient, TableBlock


@dataclass(slots=True)
class CorpusCase:
    name: str
    document: MemoDocument


UNITS = [
    "1st Battalion, 22d Infantry Regiment",
    "4th Engineer Battalion",
    "528th Sustainment Brigade",
    "1st Signal Brigade",
    "82d Airborne Division Staff",
]

STREETS = [
    "123 Wetzel Road",
    "588 Victory Drive",
    "44 Bastogne Loop",
    "900 Liberty Avenue",
]

CITIES = [
    "Fort Liberty, NC 28310",
    "Fort Carson, CO 80913",
    "Fort Cavazos, TX 76544",
    "Joint Base Lewis-McChord, WA 98433",
]

SUBJECTS = [
    "Updated Staff Duty Procedures",
    "Motor Pool Safety Inspection Results",
    "Signal Equipment Turn-In Schedule",
    "Training Holiday Leave Coordination",
    "Quarterly Counseling Program Status",
]

NAMES = [
    "Jordan A. Carter",
    "Taylor M. Brooks",
    "Avery R. James",
    "Cameron L. Bell",
    "Riley P. Hayes",
]

RANKS = ["CPT", "MAJ", "1LT", "SFC", "MSG"]
BRANCHES = ["EN", "IN", "SC", "MI", "LG"]
TITLES = [
    "Executive Officer",
    "Operations Officer",
    "Company Commander",
    "First Sergeant",
    "Maintenance Control Officer",
]

POINTS = [
    "Conduct a weekly review of suspense-driven actions and record the status in the tracker.",
    "Ensure subordinate leaders acknowledge all taskings before the end of the duty day.",
    "Submit corrected rosters in a single consolidated package to the battalion staff.",
    "Coordinate vehicle dispatches at least 24 hours before the planned movement window.",
    "Route unresolved administrative issues through the S-1 before elevating them to command.",
]


def generate_corpus(seed: int = 7, count: int = 24) -> list[CorpusCase]:
    rng = Random(seed)
    cases: list[CorpusCase] = []
    for index in range(count):
        document = _make_document(rng, index)
        cases.append(CorpusCase(name=f"case_{index:03d}", document=document))
    return cases


def _make_document(rng: Random, index: int) -> MemoDocument:
    memo_type = rng.choice(
        ["MEMORANDUM FOR RECORD", "MEMORANDUM FOR", "MEMORANDUM THRU"]
    )
    for_recipients = [_recipient(rng)]
    if memo_type == "MEMORANDUM FOR":
        if rng.random() > 0.55:
            for_recipients.append(_recipient(rng))
    elif memo_type == "MEMORANDUM THRU":
        for_recipients = [_recipient(rng)]
    else:
        for_recipients = []

    thru_recipients = [_recipient(rng)] if memo_type == "MEMORANDUM THRU" else []
    body = _make_body(rng, index)

    month = rng.choice(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
    )
    day = f"{rng.randint(1, 28):02d}"
    year = 2024 + (index % 2)

    enclosures = []
    if rng.random() > 0.6:
        enclosures = [f"Roster {index + 1}", "Inspection Worksheet"]

    return MemoDocument(
        unit_name=rng.choice(UNITS),
        unit_street_address=rng.choice(STREETS),
        unit_city_state_zip=rng.choice(CITIES),
        office_symbol=f"{rng.choice(['S1', 'S2', 'S3', 'S4', 'CMD'])}-{100 + index}",
        subject=rng.choice(SUBJECTS),
        body=body,
        author_name=rng.choice(NAMES),
        author_rank=rng.choice(RANKS),
        author_branch=rng.choice(BRANCHES),
        author_title=rng.choice(TITLES),
        memo_type=memo_type,
        todays_date=f"{day} {month} {year}",
        for_recipients=for_recipients,
        thru_recipients=thru_recipients,
        suspense_date=f"{day} {month} {year}" if rng.random() > 0.75 else None,
        enclosures=enclosures,
        distros=["A", "B"] if rng.random() > 0.82 else [],
        cfs=["Commander"] if rng.random() > 0.88 else [],
        authority="FOR THE COMMANDER:" if rng.random() > 0.9 else None,
    )


def _make_body(rng: Random, index: int) -> list[BodyItem | TableBlock]:
    items: list[BodyItem | TableBlock] = []
    for item_index in range(rng.randint(3, 5)):
        base = BodyItem(paragraphs=[rng.choice(POINTS)])
        if rng.random() > 0.55:
            base.paragraphs.append(
                "Point of contact is the undersigned at DSN 555-0100 or "
                "army.team@example.mil."
            )
        if rng.random() > 0.45:
            base.children = [
                BodyItem(paragraphs=[rng.choice(POINTS)]),
                BodyItem(paragraphs=[rng.choice(POINTS)]),
            ]
            if rng.random() > 0.6:
                base.children[1].children = [
                    BodyItem(paragraphs=["Provide an updated status during the next sync meeting."]),
                    BodyItem(paragraphs=["Capture unresolved issues in the tracker before close of business."]),
                ]
        items.append(base)
        if item_index == 1 and index % 3 == 0:
            items.append(
                TableBlock(
                    headers=["Last Name", "Duty Position", "Status"],
                    rows=[
                        ["Smith", "Shift Leader", "Ready"],
                        ["Jones", "Vehicle NCO", "Pending"],
                    ],
                )
            )
    return items


def _recipient(rng: Random) -> Recipient:
    return Recipient(
        name=rng.choice(
            [
                "Commander, 1st Brigade Combat Team",
                "Director, Garrison Human Resources",
                "Chief, Plans and Operations",
                "Command Sergeant Major, Division Headquarters",
            ]
        ),
        street_address=rng.choice(STREETS),
        city_state_zip=rng.choice(CITIES),
    )
