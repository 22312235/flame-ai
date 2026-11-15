# FLAME AI — Cinematic React Prototype (v4)

## Run locally on Windows

**Important:** `package.json` is inside the `flame-ai` subfolder, not in the outer extracted folder.

1. Extract this ZIP.
2. Open the extracted `flame-ai-cinematic-refined-v4` folder.
3. Open the inner **flame-ai** folder in VS Code (you should see `package.json` in the Explorer).
4. Open the VS Code terminal and run:

```powershell
npm.cmd install
npm.cmd run dev
```

If you are already in the outer folder, run:

```powershell
cd .\flame-ai
npm.cmd install
npm.cmd run dev
```

## What's changed in v4

- Replaced the flame-shaped brand mark with the NASA meatball logo.
- Made the header fixed with a translucent background so navigation stays available while scrolling.
- Added hash-based page navigation (`#home`, `#explorer`, `#insights`, `#assistant`, `#compare`) so pages can be opened directly and browser back/forward works.
- Kept the existing React pages and their interactions (catalogue search/filters, record details, compare selection and assistant demo).
- Refined content margins, page top spacing, hover feedback, animated wave lines and page transitions.
- Added reduced-motion accessibility support.

## Notes

This is still a frontend prototype. The assistant's answers are demo responses until the team's API is connected. The NASA logo is loaded from Wikimedia Commons; it requires an internet connection. Some photography is remotely hosted and also requires internet access.
