# Change classification taxonomy

How to classify diff hunks into behavior-change classes and what each class
implies for device test selection.

## Classes and signals

| Class | Typical signals in the diff | Default implication |
|---|---|---|
| `screen_added` | new route/screen registration, new navigation entry, new Activity/ViewController/composable screen | `create_then_run` for the new journey; `run_unchanged` for the navigation smoke |
| `screen_removed` | route/screen deregistered, navigation entry deleted, files removed | `retire_candidate` for tests whose only target is the removed screen; check links into it |
| `flow_changed` | navigation order changed, new/removed steps in a journey, conditional branches, feature-flag gating of a path | `update_then_run` for tests of that journey; smoke dependency check |
| `validation_changed` | form validators, required fields, error conditions, input constraints | `update_then_run` for validation tests; `create_then_run` when a new rule has no coverage |
| `label_changed` | accessible names, visible button/menu text, content descriptions, test ids | `update_then_run` for tests that reference the old label; prefer semantic updates |
| `api_contract_changed` | client request/response models, endpoints, status handling, auth headers that alter UI behavior | run the journeys that render that data; `investigate` when the UI effect is unclear |
| `copy_only` | string changes with no behavior/validation/label-assertion effect | usually `not_impacted`; `update_then_run` only for tests asserting that exact copy |
| `style_only` | colors, spacing, themes, assets with no layout-behavior effect | usually `not_impacted` for functional tests |
| `unknown` | generated code, build config, large refactors with unclear UI effect | `investigate` — never silently dropped |

A single diff usually produces several classes; classify per hunk/area, not
per PR.

## Mapping evidence priority

When connecting a classified change to saved tests/scenarios, trust in this
order:

1. explicit `qyrion.yml` `journeys[].paths` mappings and tags
2. saved-test objective/steps that name the changed screen, flow, or label
   (`qyrion tests get <id> --json`)
3. repo call graph / component ownership (who renders the changed code)
4. name similarity — weak signal, never sufficient alone for a mutation

## Worked example

Diff adds a required "Company" field to the checkout form
(`validation_changed` + `label_changed` on checkout):

- checkout happy-path saved test → `update_then_run` (fill the new field)
- required-field validation test → `update_then_run` (assert the new error)
- business-account checkout scenario → `create_then_run` if business
  behavior differs and has no coverage
- product-search tests → `not_impacted`
- saved test for a removed alternate checkout route → `retire_candidate`
  (proposal only)

## Hard rules

- Never delete a saved test. `retire_candidate` output is a proposal with
  the evidence for obsolescence; a human decides.
- Never convert a low-confidence mapping into a test mutation without user
  review.
- If deployment/build freshness is unconfirmed, produce the plan but state
  that running it would not validate this change.
