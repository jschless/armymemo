#let render_route_paragraph(paragraph) = {
  if paragraph.lines.len() > 0 {
    block(width: 100%)[#paragraph.lines.at(0)]
  }
  for line in paragraph.lines.slice(1) {
    v(layout.spacing.route_wrap)
    pad(left: pt(paragraph.continuation_indent_pt))[
      #block(width: 100%)[#line]
    ]
  }
  v(pt(paragraph.paragraph_gap_pt))
}

#let render_route_section(memo) = {
  for paragraph in memo.route_paragraphs {
    render_route_paragraph(paragraph)
  }
}

#let render_table_node(node) = {
  align(center)[
    #table(
      columns: node.column_count,
      align: left,
      stroke: 0.5pt,
      inset: (x: 6pt, y: 2pt),
      ..node.cells,
    )
  ]
  v(layout.spacing.body_item)
}

#let render_node(node) = {
  if node.kind == "table" {
    render_table_node(node)
  } else {
    pad(left: pt(node.first_line_indent_pt))[
      #table(
        columns: (pt(node.continuation_indent_pt - node.first_line_indent_pt), 1fr),
        stroke: none,
        inset: 0pt,
        column-gutter: 0pt,
        align: (left, left),
        [#node.label],
        [#par(leading: layout.paragraph_leading)[#node.paragraphs.at(0)]],
      )
    ]
    for paragraph in node.paragraphs.slice(1) {
      v(layout.spacing.body_paragraph)
      pad(left: pt(node.continuation_indent_pt))[
        #par(leading: layout.paragraph_leading)[#paragraph]
      ]
    }
    v(layout.spacing.body_item)
    for child in node.children {
      render_node(child)
    }
  }
}
