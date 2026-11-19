# FLAME2023Open.zip: inspection and licence review procedure

Goal: decide, file by file, whether each member of `FLAME2023Open.zip` may be used in this commercial
project **before** anything is extracted or loaded. Licence evidence:
`docs/licenses/FLAME_licence_record_2026-11-19.md`. Results go into Section A of
`docs/licenses/LICENCE_MANIFEST.md`.

## 1. Download (you, through your own authorised account)
1. Sign in at https://flame.is.tue.mpg.de/ and open **Downloads**.
2. Download **only** `FLAME2023Open.zip` (the "FLAME 2023 Open" entry). Read the **Open Model License** shown
   on the site. Do not download any other FLAME item.
3. Note the download date and the exact link text and URL you used. These go into the manifest.
4. Place the archive, **without extracting it**:
   ```
   mkdir -p third_party/flame2023_open
   mv ~/Downloads/FLAME2023Open.zip third_party/flame2023_open/
   git status --short third_party/      # must print nothing (the folder and *.zip are git-ignored)
   ```

## 2. Inspect (read-only)
```
scripts/inspect_flame_zip.sh
```
It prints, and saves to `output/flame_inspection_<timestamp>_<pid>.txt`:
1. archive size, SHA-256, type;
2. CRC integrity test of every member (in memory);
3. full listing with permissions, sizes and dates;
4. safety checks: path traversal, symlinks, encryption, nested archives, extreme compression ratios;
5. SHA-256 and detected file type of every member (streamed, not written to disk);
6. the **full text** of any licence, readme, notice or citation document inside the archive;
7. for pickle files, the Python modules the pickle would import, found by disassembly only and **never unpickled**,
   with anything other than numpy, scipy.sparse or chumpy flagged;
8. for `.npz` files, member names and sizes only.

Send me the saved file. Nothing is extracted or loaded at this stage.

## 3. Review rules (applied by Claude, confirmed by you)

**Stop the whole review** (nothing is used) if any of the following happens:
- the integrity test fails;
- any safety flag is raised;
- a licence document inside the archive conflicts with the website's Open Model License (e.g. says
  "non-commercial" or "academic").

In that case we contact flame@tuebingen.mpg.de before going further.

Each member is then classified:

| Status | Rule |
|---|---|
| **verified** | The file is part of "the FLAME 2023 Open model, and software" (the Open Model License's scope), **and** nothing inside the archive attaches a different or additional licence to it, **and** (for pickles) it imports only numpy, scipy.sparse or chumpy. |
| **excluded** | Any of: its own licence or a readme note puts it under a non-commercial or other licence; it is a separately released FLAME resource (vertex masks, landmark embeddings, texture space, older models, D3DFACS data) not named by the Open Model License; its pickle imports anything unexpected; its purpose can't be identified. **Unclear means excluded.** |
| **pending** | Plausibly part of the Open model, but the archive and website don't settle it (e.g. a template mesh whose UV coordinates might come from the separately licensed texture work). It stays unused until it is resolved in writing (website text or an answer from flame@tuebingen.mpg.de) and then becomes verified or excluded. |

## 4. After the review
1. The manifest's Section A is filled in: one row per member, with SHA-256, size, source, licence, commercial use,
   redistribution and status.
2. **Only verified files** are extracted into `third_party/flame2023_open/`, by a script that extracts them by
   name and checks each SHA-256 against the manifest. Excluded and pending files are never extracted.
3. The FLAME loader accepts only files whose SHA-256 is listed as verified.
4. The archive itself stays **local and git-ignored**. It isn't committed to GitHub (your instruction).
5. `ATTRIBUTION.md` (credit, licence link, changes made) is written before any output that uses FLAME is shared.
