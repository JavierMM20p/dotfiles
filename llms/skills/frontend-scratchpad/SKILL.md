---
name: frontend-scratchpad
description: Offers, then builds, a temporary browser scratchpad where the user compares many design options (colors, type, layout, component treatments, backgrounds, shaders, motion) on a live preview before UI is implemented. Use when a request will create a new page, view, panel, dialog, drawer or other UI surface with components the codebase does not already have, including feature requests that never mention design, and for redesigns or significant new visual elements. Skip backend-only work, small tweaks, and screens built only from existing components.
---

# Frontend scratchpad

The user picks design options in a browser before you implement them. The page is prebuilt: you write a JSON spec and run a script. Never read `assets/scratchpad.html`; it only matters to the script.

## 1. Offer it

Offer before writing UI code when the work adds a UI surface (page, view, panel, dialog, drawer, onboarding step, dashboard section) with at least one component the codebase does not have, or is a redesign or significant new visual element. Do not offer for backend-only work, small tweaks, or screens assembled only from existing components. Skip the question if the user already asked for a scratchpad; do not offer if they declined one for this work.

Ask one short question, with the client's question tool if it has one, otherwise in text, ending the turn:

> This adds <surface> with new components. Compare design options in a scratchpad first?
> 1. No, just build it
> 2. Yes, pick what to compare
> 3. Yes, I'll choose what to compare

For answer 3, list the candidate groups and let the user pick. For answer 1, continue normally.

## 2. Prepare

```bash
python3 scripts/scratchpad.py prepare <project-root> --name <short-name>
```

It creates a temporary directory outside the repository and prints it, with the project's stack, CSS custom properties, fonts and existing components. Use this summary instead of reading stylesheets.

## 3. Choose groups and options

Decide what to compare from the brief before thinking about how to encode it. Design judgment comes from the frontend-design skill or the project's design system; this skill adds none.

- Groups are the decisions that matter for this surface: whichever of palette, typography, layout, specific component treatments, background, imagery, motion, density or others it actually needs. Decisions not explored keep the project's existing values.
- Prefer many options per group. Each must be a direction you would defend for this brief and clearly different from the others; drop near-duplicates.
- The page has no presets and every kind of option (CSS, markup, SVG, canvas, GLSL, JS) costs about the same to write. Choose by fit, never by ease. Never drop or simplify an option because it is harder to encode.
- Use real content from the brief and project, and show the states that carry design decisions (for example populated and empty).
- Do not mark a recommendation or order options by preference; the page shuffles them. Labels describe the option in a few words.

## 4. Write the spec and build

Read [references/spec.md](references/spec.md), write `spec.json` in the scratchpad directory, then run:

```bash
python3 scripts/scratchpad.py build <scratchpad-directory>
```

If it reports errors, edit only the parts of `spec.json` that need fixing and build again. The script opens the page in a browser. Do not screenshot or review the page yourself; the user reviews it.

End the turn with the page path and: "Pick options, press Copy choices and paste the result here. Notes and 'None of these fit' per group help the next round."

## 5. Act on the reply

- Chosen options: implement them in the project's own stack and conventions, reusing the chosen options' code from `spec.json`. If the directory is gone, work from the values in the pasted text.
- Groups marked "none fit": use the notes, replace those groups' options with new, different ones, keep the other groups, and build the same directory again.
- A free-text reply is fine; map it to option labels.
