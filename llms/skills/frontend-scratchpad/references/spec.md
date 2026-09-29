# Scratchpad spec

`spec.json` describes one preview document and the options that change it. Put everything options share in the top-level fields; each option holds only what it changes. Values below are placeholders, not suggestions.

```json
{
  "title": "<surface name>",
  "html": "<body markup; mark regions options can replace with data-slot=\"<slot>\">",
  "css": "<shared CSS using var(--<token>) and [data-<group-id>=\"<option-id>\"] selectors>",
  "vars": {"--<token>": "<base value>"},
  "groups": [
    {"id": "<group-id>", "label": "<group name>", "options": [
      {"id": "<option-id>", "label": "<few-word description>", "vars": {"--<token>": "<value>"}},
      {"id": "<option-id>", "label": "<few-word description>", "css": "<css>", "slots": {"<slot>": "<markup>"}}
    ]}
  ]
}
```

## Top-level fields

| Field | Meaning |
| --- | --- |
| `html` | Required. Body markup of the preview. |
| `css` | Shared styles. |
| `vars` | Base custom properties, set on `:root`. |
| `fonts` | Fonts always loaded: Google Fonts `family` values such as `"<Family>:wght@400;700"`, or full stylesheet URLs. |
| `head` | Extra markup for `<head>`, such as a script or stylesheet from a CDN. |
| `js` | Shared module script, run after the body. |
| `include` | Project stylesheets inlined before `css`, as paths relative to the project root. Use to reuse the project's real base styles. |
| `tailwind` | `true` only when the project uses Tailwind; loads Tailwind 4 in the browser and treats all CSS as Tailwind CSS. |
| `groups` | Required. Each has `id` (lowercase, digits, hyphens), `label`, and at least 2 `options`. |

## Option fields

Each option needs `id` and `label`. Any combination of these applies while it is selected:

| Field | Meaning |
| --- | --- |
| `vars` | Custom properties merged over the base values. |
| `css` | Styles added after the shared CSS. |
| `slots` | `{"<slot>": "<markup>"}` replacing the content of every `[data-slot="<slot>"]` element. Use for structurally different layouts or components. |
| `fonts`, `head`, `js` | Same as the top-level fields, only while selected. |
| `shader` | `{"target": "<selector>", "frag": "<GLSL>", "uniforms": ["--<token>"]}` or a list of them. |

Every selection also sets `data-<group-id>="<option-id>"` on `<html>`, so shared CSS or JS can react to any option.

## Shaders

A shader draws on a canvas placed behind the target element's content. Write a WebGL2 fragment shader body; the page adds this header unless the source has its own `#version` line:

```glsl
#version 300 es
precision highp float;
uniform float u_time;        // seconds; fixed when reduced motion is on
uniform vec2 u_resolution;   // canvas size in pixels
uniform vec2 u_mouse;        // pointer position over the target, 0 to 1
out vec4 fragColor;
```

Each entry in `uniforms` names a custom property and becomes a uniform with `--` replaced by `u_` and hyphens by underscores (`--<token>` becomes `u_<token>`). It is a `float` when the property is numeric, otherwise a `vec4` color, read every frame so palette options also recolor the shader. Scripts can call `scratchpad.shader(target, frag, uniforms)` and `scratchpad.readVar(name)` directly.

## Preview assembly

Each preview is a full document in its own frame: fonts, `head` fields, `:root` vars, shared `css`, then selected options' `css`, then the body with slots filled, then shaders and scripts. Media and container queries respond to the preview width the user selects. Links and form submissions never navigate; `#id` links scroll to the element. Script and shader errors appear in the page's panel.
