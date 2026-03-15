# Army Memo Rule Inventory

This document defines the current deterministic rule inventory for the standalone Army memo library. The goal is to make memo rendering a pure function of memo inputs plus a rulebook, instead of a collection of renderer heuristics.

## Source hierarchy

The rule inventory uses a strict source hierarchy.

1. AR 25-50 text is the normative source.
2. AR 25-50 figures define visual placement where the prose is incomplete.
3. Historical implementation notes from the pre-extraction LaTeX memo class are a calibration aid, not the authority.

The machine-readable source of truth is `armymemo/resources/rules/memo_rulebook.yaml`.

## Deterministic model

The Typst renderer should behave deterministically from:

- memo metadata and body structure
- the rulebook layout constants
- rule predicates such as `authority_present`, `page_number > 1`, or `multiple_recipients_or_thru`

That means:

- page geometry is not guessed from prior PDFs
- continuation-page layout is not inferred from output drift
- spacing and indent behavior are selected by rule
- reviewer checks can point back to named rules

## Core extracted rules

### Page

- Use standard letter paper.
- Use 1-inch left, right, and bottom margins.
- Do not justify the right margin.
- First-page top space is consumed by the seal and letterhead region.

### Heading

- Use block style with heading, body, and closing.
- Place the office symbol on the second line below the seal.
- Place the date flush right on the office-symbol line.
- If a suspense date exists, place it two lines above the office-symbol line at the right margin.
- Place `MEMORANDUM FOR`, `THRU`, and related route lines flush left.
- Use a hanging indent for wrapped multi-recipient route lines.
- Place `SUBJECT:` flush left below the route block.

### Body

- Single-space text.
- Double-space between paragraphs and subparagraphs.
- Do not number a one-paragraph memorandum.
- For multi-paragraph memorandums, use the hierarchy `1.`, `a.`, `(1)`, `(a)`.
- Use fixed first-line indentation by paragraph level rather than ad hoc wrapping.
- Wrapped body lines return to the left margin instead of hanging under the paragraph label.

### Closing

- If present, the authority line is uppercase and flush left.
- The authority line is on the second line below the last line of text.
- The signature block begins at center on the fifth line below the authority line.
- If there is no authority line, the signature block begins on the fifth line below the last line of the text.
- Enclosures align with the left margin on the same vertical band as the signature block.
- `DISTRIBUTION:` and `CF:` appear below the lower closing elements in fixed order.

### Continuation pages

- Place the office symbol at the left margin 1 inch from the top edge.
- Place the subject on the next line below the office symbol.
- Begin continuation text on the third line below the subject.
- Do not split a 3-line paragraph across pages.
- Keep at least two lines of a split paragraph on each page.
- Keep at least two words of a split sentence on each page.
- Do not hyphenate a word across pages.
- Do not place the authority line and signature block on a continuation page unless enough body text precedes them.
- Center the page number approximately 1 inch from the bottom.

## Current layout constants

The current Typst renderer reads layout constants from the rulebook and maps them into Typst in `armymemo/resources/typst/config.typ`.

Important current values:

- left and right margins: `72pt`
- first-page letterhead top line: `36pt`
- `DEPARTMENT OF THE ARMY`: `10pt` Arial bold
- remaining letterhead lines: `8pt` Arial bold
- letterhead inter-line gap: `2pt`
- office-symbol line top on first page: `132pt`
- continuation-page office symbol top: `72pt`
- continuation-page subject top: `88pt`
- route block gap after office line: `36pt`
- body item gap: `20pt`
- signature gap without authority line: `58pt`
- signature gap with authority line: `66pt`

These values should continue to move out of ad hoc template code and into named rules as we refine the figure-derived geometry.

## Reviewer direction

The reviewer should evolve toward data-driven checks keyed by rule ID. Examples:

- `memo.page.margins`
- `memo.heading.office_symbol`
- `memo.body.spacing`
- `memo.closing.signature`
- `memo.continuation.page_number`

That will let failures report:

- which rule failed
- whether the rule came from regulation text, figure interpretation, or implementation-derived calibration
- which rendered evidence caused the failure

## Known gaps

- We do not yet have a locally vendored copy of the official AR 25-50 PDF with figure-by-figure extraction.
- Some constants are still figure-derived or LaTeX-derived rather than directly measured from the regulation figures.
- Table layout is still not part of the strict parity target.

## Source notes

The current rule inventory was extracted from:

- AR 25-50 public excerpts covering memorandum format, spacing, and continuation pages:
  - <https://fliphtml5.com/kbhsd/jrux/AR_25-50_Preparing_and_Managing_Correspondence_2020/>
  - <https://fliphtml5.com/kbhsd/jrux/AR_25-50_Preparing_and_Managing_Correspondence_2020/16/>
  - <https://www.armywriter.com/r25-50.pdf>
  - <https://home.army.mil/wood/application/files/3015/5751/8343/AR_25_50_Army_Correspondence.pdf>
- Historical notes from the legacy LaTeX class used during extraction, not shipped in this repo
