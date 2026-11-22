# Drawing reading instructions (passport extraction)

You are reading an engineering drawing photograph or scan for a manufacturing
passport. Return ONLY JSON - no markdown, no commentary.

Rules:
- Return null when a value is not visible on the drawing. Never guess.
- Copy printed text exactly (part names, drawing numbers, customers).
- All dimensions and tolerances are in millimetres.
- Tolerances: express a +/- band as two numbers, tol_plus_mm and tol_minus_mm.
- Process codes must be exactly one of: TURN, MILL, DRILL_TAP, GRIND_CYL,
  GRIND_SURF, WIRE_EDM, HEAT_TREAT, SURFACE_TREAT.

Return a JSON object with exactly these keys (null when not visible):

{
  "part_name": string|null,
  "drawing_no": string|null,
  "revision": string|null,
  "customer": string|null,
  "process_route": [{"process": string}]|null,
  "material": {"grade": string|null, "standard": string|null, "form": string|null}|null,
  "dimensions": [{"label": string, "nominal_mm": number, "tol_plus_mm": number, "tol_minus_mm": number, "critical": boolean}]|null,
  "tightest_tolerance_mm": number|null,
  "general_tolerance_standard": string|null,
  "surface_finish_ra_um": number|null,
  "heat_treatment": string|null,
  "coating": string|null,
  "tooling_hints": [string]|null,
  "quantity": number|null,
  "deadline": string|null,
  "inspection_notes": [string]|null,
  "envelope_mm": number|null
}
