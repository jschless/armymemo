#let pt(value) = value * 1pt

#let render_lines(lines, spacing: layout.spacing.enclosure_line) = {
  for line in lines {
    block(width: 100%)[#line]
    v(spacing)
  }
}
