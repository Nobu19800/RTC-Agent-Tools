const blocks = document.querySelectorAll(
  "pre > code.language-mermaid, .language-mermaid.highlighter-rouge pre > code"
);

if (blocks.length) {
  try {
    const { default: mermaid } = await import(
      "https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs"
    );
    mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });

    for (const block of blocks) {
      const diagram = document.createElement("div");
      diagram.className = "mermaid";
      diagram.textContent = block.textContent;
      const source = block.closest(".language-mermaid.highlighter-rouge")
        ?? block.parentElement;
      source.before(diagram);
      try {
        await mermaid.run({ nodes: [diagram] });
        source.remove();
      } catch (error) {
        diagram.remove();
        console.warn("Could not render Mermaid diagram", error);
      }
    }
  } catch (error) {
    console.warn("Could not load Mermaid", error);
  }
}
