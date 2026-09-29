---
name: frontend-scratchpad
description: Use before writing UI for any feature that adds a user-visible surface or control whose layout, placement or visual treatment the user has not specified, such as a screen, panel, sheet, dialog, drawer, settings section or control group. This includes mostly-backend features that add UI, requests that never mention design, redesigns, and native apps (Android Compose, SwiftUI, Flutter) as well as web. Offers, then builds, a temporary browser scratchpad where the user compares design options on a live preview. Skip only when there is no visual decision to make: backend-only work, copy or bug fixes, or UI that repeats an existing pattern exactly (another row in an existing list, another option in an existing chip group).
---

# Frontend scratchpad

The user picks design options in a browser before you implement them. The page is prebuilt: you write a JSON spec and run a script. Never read `assets/scratchpad.html`; it only matters to the script.

## 1. Offer it

Offer when you are about to decide on your own how something new looks or where it goes: a screen, panel, sheet, dialog, drawer, settings section, control group, redesign or significant new visual element. Reusing existing components does not exempt the work: arranging existing sliders, chips and sheets into a new panel is still a design decision. Decide at planning time, before any code, even when the UI is a small part of a mostly-backend task.

Do not offer when there is no visual decision to make: backend-only work, copy or bug fixes, or UI that repeats an existing pattern exactly, such as another row in an existing list or another option in an existing chip group. Skip the question if the user already asked for a scratchpad; do not offer if they declined one for this work.

Ask one short question, with the client's question tool if it has one, otherwise in text, ending the turn:

> This adds <surface>, and its layout and look are not specified. Compare design options in a scratchpad first?
> 1. No, just build it
> 2. Yes, pick what to compare
> 3. Yes, I'll choose what to compare

For answer 3, list the candidate groups and let the user pick. For answer 1, continue normally.

## 2. Prepare

```bash
python3 scripts/scratchpad.py prepare <project-root> --name <short-name>
```

It creates a temporary directory outside the repository and prints it, with the project's stack, fonts and existing components, plus CSS custom properties for web projects or theme values (colors, color scheme roles, text styles, shapes) for Android, SwiftUI and Flutter projects. Use this summary instead of reading stylesheets or theme files.

For non-web projects the scratchpad is an HTML mockup. Copy the theme's colors, type and shapes from the summary, or the theme files it names, into the spec's `vars`, and draw native controls in HTML and CSS to match how they look in the app. Do not use `include` or `tailwind`.

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

- Chosen options: implement them in the project's own stack and conventions, reusing the chosen options' code from `spec.json`, or for native projects translating its values into theme code. If the directory is gone, work from the values in the pasted text.
- Groups marked "none fit": use the notes, replace those groups' options with new, different ones, keep the other groups, and build the same directory again.
- A free-text reply is fine; map it to option labels.
