#let render_memo(memo, logo_path: "DA_LOGO.png") = {
  set page(
    paper: "us-letter",
    margin: layout.page_margin,
    header-ascent: layout.header_ascent,
    footer-descent: layout.footer_descent,
    footer: render_page_footer(),
    foreground: render_page_foreground(memo, logo_path),
  )
  set text(font: layout.font_family, size: layout.font_size)
  set par(justify: false, spacing: 0pt, leading: layout.paragraph_leading)
  set block(spacing: 0pt)
  render_opening_block(memo)
  render_route_section(memo)
  block(width: 100%)[SUBJECT: #memo.subject]
  v(layout.spacing.after_subject_line)
  render_nodes(memo.body, sticky_last: true)
  render_closing_block(memo)
}
