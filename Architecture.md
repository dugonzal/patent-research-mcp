# Architecture

Google Patents → fetch() → raw/
                    ↓
              get_sections() → sections/
                    ↓
              ArchitectureCard → cards/
              ClaimsFirewall   → claims/
              PatternCard      → patterns/
                    ↓
              export() → exports/

## Components
server.py, patents.py, extractor.py, registry.py, probe.py,
schemas.py, store.py, prompts.py, exporter.py, normalizer.py
