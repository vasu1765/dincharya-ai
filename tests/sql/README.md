# SQL test scope

Future database tests must use synthetic fixtures in the isolated test stack.
Cover object inventory and function signatures, recurrence/date boundaries,
conflict detection, validation, duplicate decisions, approval concurrency, and
reminder delivery uniqueness. No production SQL is executed by offline tests.
The fixture schema is synthetic and does not claim to reproduce live behavior.
