# Evaluation Schema

## Goal
Convert evaluation from simple pass/fail into diagnostic evaluation that explains where the system succeeds or fails.

## Each evaluation sample should contain

- `id`: unique string id for the test case
- `question`: user query
- `expected_answer`: short expected answer or judgment target
- `category`: one of
  - `definition`
  - `punishment`
  - `section_lookup`
  - `concept`
  - `out_of_scope`
- `law`: one of
  - `penal_code`
  - `contract_act`
  - `other`
  - `none`
- `expected_sections`: list of gold section ids or section references
- `difficulty`: one of
  - `easy`
  - `medium`
  - `hard`
- `should_refuse`: boolean
- `notes`: optional string for evaluator comments

## Example sample

```json
{
  "id": "pc_theft_definition_001",
  "question": "What is theft under Bangladesh law?",
  "expected_answer": "Definition of theft under the Penal Code with correct section grounding.",
  "category": "definition",
  "law": "penal_code",
  "expected_sections": ["Penal Code 378"],
  "difficulty": "easy",
  "should_refuse": false,
  "notes": "Tests definition lookup, not punishment."
}
