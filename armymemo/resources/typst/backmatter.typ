#let render_enclosures(memo) = {
  if memo.enclosure_label != none {
    block(width: 100%)[#memo.enclosure_label]
    v(layout.spacing.enclosure_line)
  }
  for line in memo.enclosure_entries {
    block(width: 100%)[#line]
    v(layout.spacing.enclosure_line)
  }
}

#let render_signature_block(memo) = {
  table(
    columns: (1fr, 1fr),
    stroke: none,
    inset: 0pt,
    column-gutter: 0pt,
    [
      #render_enclosures(memo)
    ],
    [
      #align(left)[
        #render_lines(memo.signature_lines)
      ]
    ],
  )
}

#let render_trailing_list(title, values, top_gap: layout.spacing.distribution_gap) = {
  if values.len() > 0 {
    v(top_gap)
    block(width: 100%)[#title]
    v(layout.spacing.enclosure_line)
    block(width: 100%)[#values.at(0)]
    for value in values.slice(1) {
      v(layout.spacing.enclosure_line)
      block(width: 100%)[#value]
    }
  }
}
