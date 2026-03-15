#let render_page_footer() = context {
  if counter(page).get().first() > 1 [
    #align(center)[#counter(page).display()]
  ]
}

#let render_page_foreground(memo, logo_path) = context {
  if counter(page).get().first() == 1 [
    #place(top + left, dx: layout.letterhead.logo_dx, dy: layout.letterhead.logo_dy)[#image(logo_path, height: layout.letterhead.logo_height)]
    #place(top + center, dx: layout.letterhead.header_dx, dy: layout.letterhead.header_top)[#text(size: 10pt, weight: "bold")[DEPARTMENT OF THE ARMY]]
    #place(top + center, dx: layout.letterhead.header_dx, dy: layout.letterhead.header_top + layout.letterhead.header_line_step)[#text(size: 8pt, weight: "bold")[#memo.unit_name]]
    #place(top + center, dx: layout.letterhead.header_dx, dy: layout.letterhead.header_top + layout.letterhead.header_line_step * 2)[#text(size: 8pt, weight: "bold")[#memo.unit_street_address]]
    #place(top + center, dx: layout.letterhead.header_dx, dy: layout.letterhead.header_top + layout.letterhead.header_line_step * 3)[#text(size: 8pt, weight: "bold")[#memo.unit_city_state_zip]]
    #if memo.suspense_date != none [
      #place(top + right, dx: -layout.letterhead.suspense_dx, dy: layout.letterhead.suspense_dy)[#text(weight: "bold")[S: #memo.suspense_date]]
    ]
  ] else [
    #place(top + left, dx: layout.continuation.office_dx, dy: layout.continuation.office_dy)[#block(width: 100%)[#memo.office_symbol]]
    #place(top + left, dx: layout.continuation.subject_dx, dy: layout.continuation.subject_dy)[#block(width: 100%)[SUBJECT: #memo.subject]]
  ]
}

#let render_opening_block(memo) = {
  block(width: 100%)[
    #memo.office_symbol
    #h(1fr)
    #if memo.todays_date != none [#memo.todays_date]
  ]
  v(layout.spacing.after_office_line)
}
