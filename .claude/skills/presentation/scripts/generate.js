#!/usr/bin/env node
// svaib Presentation Generator
// Usage: NODE_PATH=$(npm root -g) node generate.js <input.json> [output.pptx]
//
// Input JSON format:
// {
//   "title": "Presentation Title",
//   "slides": [
//     { "layout": "title", "title": "...", "subtitle": "..." },
//     { "layout": "bullets", "title": "...", "bullets": ["...", "..."] },
//     { "layout": "icon-text", "title": "...", "items": [{ "icon": "FaCheckCircle", "heading": "...", "text": "..." }] },
//     { "layout": "two-column", "title": "...", "leftTitle": "...", "leftBullets": [...], "rightTitle": "...", "rightBullets": [...] },
//     { "layout": "stats", "title": "...", "stats": [{ "value": "85%", "label": "..." }] },
//     { "layout": "quote", "quote": "...", "author": "..." },
//     { "layout": "section", "title": "..." }
//   ]
// }

const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// ─── svaib Brand Constants ───────────────────────────────────────────

const C = {
  teal: "008B7F",
  darkBlue: "2C3E50",
  pink: "FF4D8D",
  gray: "6B7280",
  brightTeal: "00B4A6",
  yellow: "FFD600",
  white: "FFFFFF",
  lightTeal: "F0FDFB",
  subtleTeal: "E0F7F5",
  cardBorder: "E5E7EB",
};

const FONT = { heading: "Montserrat", body: "Roboto" };

// ─── Helpers ─────────────────────────────────────────────────────────

function addBrandMarkers(slide, pres) {
  // Teal top stripe
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.04,
    fill: { color: C.teal },
  });
  // Logo: "sv" bright teal, "ai" pink, "b" bright teal
  // Position: 23.52cm × 13.26cm = 9.26" × 5.22", size: 1.87cm × 1.03cm = 0.74" × 0.41"
  slide.addText([
    { text: "sv", options: { color: C.brightTeal, bold: true, fontFace: FONT.heading, fontSize: 12 } },
    { text: "ai", options: { color: C.pink, bold: true, fontFace: FONT.heading, fontSize: 12 } },
    { text: "b", options: { color: C.brightTeal, bold: true, fontFace: FONT.heading, fontSize: 12 } },
  ], {
    x: 9.26, y: 5.22, w: 0.74, h: 0.41,
    align: "center", valign: "middle",
  });
}

async function iconToBase64Png(iconName, color, size = 256) {
  const prefix = iconName.substring(0, 2).toLowerCase();
  const libMap = { fa: "fa", md: "md", hi: "hi", bi: "bi", fi: "fi" };
  const libName = libMap[prefix];
  if (!libName) throw new Error(`Unknown icon library prefix: ${prefix}`);

  const icons = require(`react-icons/${libName}`);
  const IconComponent = icons[iconName];
  if (!IconComponent) throw new Error(`Icon ${iconName} not found in react-icons/${libName}`);

  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

function addTealAccentBar(slide, pres, x, y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.05, h: 0.3,
    fill: { color: C.teal },
  });
}

// ─── Layout: Title Slide ─────────────────────────────────────────────

function layoutTitle(slide, pres, spec) {
  slide.background = { fill: C.white };

  // Decorative teal shape (top-right corner accent)
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 7.5, y: 0.5, w: 2, h: 2,
    fill: { color: C.subtleTeal },
    rectRadius: 0.15,
  });

  // Title
  const titleParts = [];
  const titleText = spec.title || "Untitled";
  // Highlight "AI" in pink if present
  if (titleText.includes("AI")) {
    const parts = titleText.split("AI");
    for (let i = 0; i < parts.length; i++) {
      if (i > 0) {
        titleParts.push({
          text: "AI",
          options: { color: C.pink, bold: true, fontFace: FONT.heading, fontSize: 72 },
        });
      }
      if (parts[i]) {
        titleParts.push({
          text: parts[i],
          options: { color: C.teal, bold: true, fontFace: FONT.heading, fontSize: 72 },
        });
      }
    }
  } else {
    titleParts.push({
      text: titleText,
      options: { color: C.teal, bold: true, fontFace: FONT.heading, fontSize: 72 },
    });
  }

  slide.addText(titleParts, {
    x: 0.9, y: 0.5, w: 6.5, h: 3.0,
    valign: "middle", shrinkText: true,
  });

  // Subtitle
  if (spec.subtitle) {
    slide.addText(spec.subtitle, {
      x: 0.9, y: 3.7, w: 6.5, h: 0.8,
      fontFace: FONT.body, fontSize: 34,
      color: C.darkBlue, valign: "top",
    });
  }

  // Decorative circles
  slide.addShape(pres.shapes.OVAL, {
    x: 8.2, y: 3.5, w: 0.8, h: 0.8,
    fill: { color: C.brightTeal },
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 9.0, y: 4.0, w: 0.4, h: 0.4,
    fill: { color: C.yellow },
  });
}

// ─── Layout: Bullets ─────────────────────────────────────────────────

function layoutBullets(slide, pres, spec) {
  slide.background = { fill: C.white };

  // Title with accent bar
  addTealAccentBar(slide, pres, 0.5, 0.4);
  slide.addText(spec.title || "", {
    x: 0.7, y: 0.3, w: 8.5, h: 0.6,
    fontFace: FONT.heading, fontSize: 50, bold: true,
    color: C.teal, shrinkText: true,
  });

  // Bullets
  const bullets = (spec.bullets || []).map((b) => ({
    text: b,
    options: {
      bullet: true,
      fontFace: FONT.body, fontSize: 26,
      color: C.darkBlue, paraSpaceAfter: 10,
    },
  }));

  slide.addText(bullets, {
    x: 0.8, y: 1.2, w: 5.5, h: 3.5,
    valign: "top",
  });

  // Decorative card on right
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 6.8, y: 1.2, w: 2.7, h: 3.5,
    fill: { color: C.subtleTeal },
    rectRadius: 0.15,
    shadow: { type: "outer", color: C.teal, blur: 5, offset: 4, angle: 135, opacity: 0.15 },
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.5, y: 2.0, w: 1.3, h: 1.3,
    fill: { color: C.brightTeal },
  });
}

// ─── Layout: Icon + Text Rows ────────────────────────────────────────

async function layoutIconText(slide, pres, spec) {
  slide.background = { fill: C.white };

  // Title
  addTealAccentBar(slide, pres, 0.5, 0.4);
  slide.addText(spec.title || "", {
    x: 0.7, y: 0.3, w: 8.5, h: 1.0,
    fontFace: FONT.heading, fontSize: 50, bold: true,
    color: C.teal, shrinkText: true,
  });

  const items = spec.items || [];
  const rowH = Math.min(1.0, 3.2 / Math.max(items.length, 1));
  const startY = 1.6;

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const y = startY + i * rowH;

    // Icon in teal circle
    if (item.icon) {
      try {
        const iconColor = "#FFFFFF";
        const iconData = await iconToBase64Png(item.icon, iconColor, 256);
        // Teal circle background
        slide.addShape(pres.shapes.OVAL, {
          x: 0.8, y: y, w: 0.5, h: 0.5,
          fill: { color: C.teal },
        });
        // Icon on top
        slide.addImage({
          data: iconData,
          x: 0.87, y: y + 0.07, w: 0.36, h: 0.36,
        });
      } catch (e) {
        // Fallback: just teal circle
        slide.addShape(pres.shapes.OVAL, {
          x: 0.8, y: y, w: 0.5, h: 0.5,
          fill: { color: C.teal },
        });
      }
    }

    // Heading
    slide.addText(item.heading || "", {
      x: 1.5, y: y, w: 7.5, h: 0.3,
      fontFace: FONT.heading, fontSize: 26, bold: true,
      color: C.darkBlue,
    });

    // Description
    if (item.text) {
      slide.addText(item.text, {
        x: 1.5, y: y + 0.42, w: 7.5, h: 0.35,
        fontFace: FONT.body, fontSize: 18,
        color: C.gray,
      });
    }
  }
}

// ─── Layout: Two-Column ──────────────────────────────────────────────

function layoutTwoColumn(slide, pres, spec) {
  slide.background = { fill: C.white };

  // Title
  addTealAccentBar(slide, pres, 0.5, 0.4);
  slide.addText(spec.title || "", {
    x: 0.7, y: 0.3, w: 8.5, h: 0.6,
    fontFace: FONT.heading, fontSize: 50, bold: true,
    color: C.teal, shrinkText: true,
  });

  // Left column
  if (spec.leftTitle) {
    slide.addText(spec.leftTitle, {
      x: 0.8, y: 1.2, w: 4.0, h: 0.4,
      fontFace: FONT.heading, fontSize: 34, bold: true,
      color: C.darkBlue,
    });
  }
  const leftBullets = (spec.leftBullets || []).map((b) => ({
    text: b,
    options: {
      bullet: true,
      fontFace: FONT.body, fontSize: 24,
      color: C.darkBlue, paraSpaceAfter: 6,
    },
  }));
  if (leftBullets.length) {
    slide.addText(leftBullets, {
      x: 0.8, y: spec.leftTitle ? 1.7 : 1.2, w: 4.0, h: 3.0,
      valign: "top",
    });
  }

  // Divider line
  slide.addShape(pres.shapes.LINE, {
    x: 5.0, y: 1.2, w: 0, h: 3.5,
    line: { color: C.teal, width: 1.5 },
  });

  // Right column
  if (spec.rightTitle) {
    slide.addText(spec.rightTitle, {
      x: 5.3, y: 1.2, w: 4.2, h: 0.4,
      fontFace: FONT.heading, fontSize: 34, bold: true,
      color: C.darkBlue,
    });
  }
  const rightBullets = (spec.rightBullets || []).map((b) => ({
    text: b,
    options: {
      bullet: true,
      fontFace: FONT.body, fontSize: 24,
      color: C.darkBlue, paraSpaceAfter: 6,
    },
  }));
  if (rightBullets.length) {
    slide.addText(rightBullets, {
      x: 5.3, y: spec.rightTitle ? 1.7 : 1.2, w: 4.2, h: 3.0,
      valign: "top",
    });
  }
}

// ─── Layout: Stats ───────────────────────────────────────────────────

function layoutStats(slide, pres, spec) {
  slide.background = { fill: C.white };

  // Title
  addTealAccentBar(slide, pres, 0.5, 0.4);
  slide.addText(spec.title || "", {
    x: 0.7, y: 0.3, w: 8.5, h: 0.6,
    fontFace: FONT.heading, fontSize: 50, bold: true,
    color: C.teal, shrinkText: true,
  });

  const stats = spec.stats || [];
  const count = stats.length;
  const cardW = Math.min(2.5, (8.5 - 0.3 * (count - 1)) / count);
  const totalW = count * cardW + (count - 1) * 0.3;
  const startX = (10 - totalW) / 2;

  for (let i = 0; i < count; i++) {
    const x = startX + i * (cardW + 0.3);
    const stat = stats[i];

    // Card background
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.5, w: cardW, h: 2.8,
      fill: { color: C.white },
      line: { color: C.cardBorder, width: 1 },
      rectRadius: 0.1,
      shadow: { type: "outer", color: C.teal, blur: 5, offset: 4, angle: 135, opacity: 0.15 },
    });

    // Value
    slide.addText(stat.value || "", {
      x, y: 1.8, w: cardW, h: 1.2,
      fontFace: FONT.heading, fontSize: 44, bold: true,
      color: C.pink, align: "center", valign: "middle",
    });

    // Label
    slide.addText(stat.label || "", {
      x, y: 3.1, w: cardW, h: 0.8,
      fontFace: FONT.body, fontSize: 18,
      color: C.darkBlue, align: "center", valign: "top",
    });
  }
}

// ─── Layout: Quote ───────────────────────────────────────────────────

function layoutQuote(slide, pres, spec) {
  slide.background = { fill: C.lightTeal };

  // Large quotation mark
  slide.addText("\u201C", {
    x: 0.8, y: 0.5, w: 1, h: 1.5,
    fontFace: FONT.heading, fontSize: 80, bold: true,
    color: C.brightTeal,
  });

  // Quote text
  slide.addText(spec.quote || "", {
    x: 1.2, y: 1.5, w: 7.6, h: 2.5,
    fontFace: FONT.body, fontSize: 28, italic: true,
    color: C.darkBlue, valign: "middle",
  });

  // Author
  if (spec.author) {
    slide.addText(`\u2014 ${spec.author}`, {
      x: 1.2, y: 4.2, w: 7.6, h: 0.5,
      fontFace: FONT.body, fontSize: 16,
      color: C.gray, align: "right",
    });
  }
}

// ─── Layout: Section Divider ─────────────────────────────────────────

function layoutSection(slide, pres, spec) {
  slide.background = { fill: C.lightTeal };

  // Large centered title
  slide.addText(spec.title || "", {
    x: 1, y: 1.5, w: 8, h: 2.5,
    fontFace: FONT.heading, fontSize: 50, bold: true,
    color: C.teal, align: "center", valign: "middle",
  });

  // Decorative bar below
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4, y: 4.0, w: 2, h: 0.06,
    fill: { color: C.teal },
  });
}

// ─── Main ────────────────────────────────────────────────────────────

async function main() {
  const inputFile = process.argv[2];
  const outputFile = process.argv[3] || "presentation.pptx";

  if (!inputFile) {
    console.error("Usage: NODE_PATH=$(npm root -g) node generate.js <input.json> [output.pptx]");
    process.exit(1);
  }

  const spec = JSON.parse(fs.readFileSync(inputFile, "utf8"));
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "svaib";
  pres.title = spec.title || "svaib Presentation";

  const slides = spec.slides || [];
  for (const slideSpec of slides) {
    const slide = pres.addSlide();
    addBrandMarkers(slide, pres);

    switch (slideSpec.layout) {
      case "title":
        layoutTitle(slide, pres, slideSpec);
        break;
      case "bullets":
        layoutBullets(slide, pres, slideSpec);
        break;
      case "icon-text":
        await layoutIconText(slide, pres, slideSpec);
        break;
      case "two-column":
        layoutTwoColumn(slide, pres, slideSpec);
        break;
      case "stats":
        layoutStats(slide, pres, slideSpec);
        break;
      case "quote":
        layoutQuote(slide, pres, slideSpec);
        break;
      case "section":
        layoutSection(slide, pres, slideSpec);
        break;
      default:
        // Fallback: treat as bullets
        layoutBullets(slide, pres, slideSpec);
    }
  }

  await pres.writeFile({ fileName: outputFile });
  console.log(`Created: ${outputFile} (${slides.length} slides)`);
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
