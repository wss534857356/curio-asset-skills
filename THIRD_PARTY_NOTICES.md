# Third-party notices

The root MIT license covers first-party instructions, scripts, configuration examples, authored SVG heraldry and repository documentation. It does not relicense third-party components or the demonstration screenshots. Git normalizes text line endings to LF; upstream text and license wording are otherwise preserved.

## mesh-split-fill

- Author: **WentianYi2025**.
- Upstream: [WentianYi2025/mesh-split-fill](https://github.com/WentianYi2025/mesh-split-fill).
- License: MIT; [original notice](skills/mesh-split-fill/LICENSE) retained verbatim.
- Source: installed skill snapshot whose bundled README identifies release `v1.0.0`, collected 2026-09-26. An upstream commit identifier was not recorded for this installed copy.
- Included: skill instructions, references, UI metadata, Python scripts and tests. Cache files and the nested release ZIP are omitted.
- The upstream README is retained for context. Its standalone ZIP installation instructions and historic test claims refer to the upstream package, not this collection; use this repository's root installation and verification instructions.

## Meshy 3D Generation

- Author: **Meshy**.
- Upstream: [meshy-dev/meshy-3d-agent](https://github.com/meshy-dev/meshy-3d-agent).
- License: MIT; [original notice](skills/meshy-3d-generation/LICENSE) retained verbatim.
- Source: official plugin `meshy-openai-plugin` version **0.6.0**, collected 2026-09-26.
- Bundled source provenance records base commit `644fd7058aec61404dc696a6b57e292021f00d81` and a clean source tree.
- Included: `meshy-3d-generation` skill, its references, metadata and SVG icons, unchanged. The plugin manifest, other skills, runtime installation, login state and credentials are not included.
- This snapshot instructs use of **meshy-cli 0.4.0**. Review current command help and service documentation when executing paid tasks.

The MIT license on Meshy's integration instructions does not license the hosted service, account credits, trademarks or generated 3D assets. Generated-asset rights depend on the applicable plan, source inputs and terms: [Meshy ownership guidance](https://help.meshy.ai/en/articles/10137554-what-is-the-ownership-of-the-generated-models).

## Screenshots and dependencies

The deer vessel previews and the badger sculpture / balance case credit Meshy as the source-model tool; the source generation plan and a separate model-distribution grant are not recorded in this collection. The badger case includes historical task costs, which do not establish an account plan or model license. No source model is distributed. See [ASSET_NOTICE.md](ASSET_NOTICE.md) and [image provenance](docs/images/README.md).

Blender, Python, Pillow, NumPy, PyYAML, GitHub CLI and any image-generation service are external tools or dependencies with their own licenses. Their executables and credentials are not vendored here. Meshy icons retain their original upstream terms and identity; their presence does not imply endorsement.
