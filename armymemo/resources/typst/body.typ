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
}

#let render_nodes(nodes) = {
  for (index, node) in nodes.enumerate() {
    if node.kind == "table" {
      render_table_node(node)
    } else {
      par(
        leading: layout.paragraph_leading,
        first-line-indent: (amount: pt(node.first_line_indent_pt), all: true),
      )[
        #node.label#h(pt(node.label_gap_pt))#node.paragraphs.at(0)
      ]
      for paragraph in node.paragraphs.slice(1) {
        v(layout.spacing.body_paragraph)
        par(leading: layout.paragraph_leading)[#paragraph]
      }
      if node.children.len() > 0 {
        v(layout.spacing.body_item)
        render_nodes(node.children)
      }
    }
    if index < nodes.len() - 1 {
      v(layout.spacing.body_item)
    }
  }
}
