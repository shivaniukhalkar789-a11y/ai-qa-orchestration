"""Day 3 response-evaluation lab (offline-first, mock by default).

Modules:
    paths      project file locations
    contract   the four-field response contract and structural checks
    data       dataset / rubric loading and validation
    providers  mock and live (OpenAI) response providers
    fixtures   fixed, reviewed MOCK responses and clinic fixtures
    runner     runs cases through a provider and builds evidence records
    verdict    the rubric decision rule (no averaging)
    runstore   run metadata, hashing, saving, human reviews
    report     static HTML report (all text escaped)
    clinic     controlled failure clinic
    cli        argparse command line
"""
