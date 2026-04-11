# Design Foundations Reference

## Three Layers of Design

Every design operates on three layers simultaneously. All three must harmonize — a failure at any layer undermines the others.

| Layer          | Question                                                    | What It Governs                                                       |
| -------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- |
| **Purpose**    | What problem does this solve? Who is it for?                | Feature selection, content hierarchy, information architecture        |
| **Medium**     | What are the constraints of the delivery channel?           | Screen size, input modality, performance budget, browser capabilities |
| **Aesthetics** | What visual treatment serves the purpose within the medium? | Color, typography, spacing, motion, composition                       |

The layers are ordered. Purpose constrains medium choices. Medium constrains aesthetic choices. Designing aesthetics before understanding the medium produces decoration. Designing the medium before understanding the purpose produces engineering without direction.

Common failure: starting with aesthetics ("let's make it look modern") before clarifying purpose ("what is this page supposed to accomplish?"). The result is a visually polished surface that doesn't solve the right problem.

## The Fogg Credibility Study

Stanford's BJ Fogg studied how people assess the credibility of websites (2002, replicated multiple times since). Key finding:

**46% of participants assessed credibility primarily based on visual design.** Another **28% cited information design/structure** (layout, navigation, information hierarchy).

Combined: **~75% of credibility judgment comes from design, not content.**

What this means for product work:

- Visual quality is not cosmetic — it directly affects whether users trust the product
- A well-written product with poor visual design loses credibility before users read the copy
- Design investment has measurable ROI in trust, conversion, and retention
- First impressions form in milliseconds — users decide to stay or leave before they read

This is why Form's work matters early, not late. Delaying visual design until after "the features work" means launching with a credibility deficit that no amount of good engineering compensates for.

## The Design Sequence

The correct order for design work:

```
1. Personas      → Who is the user? What are their goals, constraints, context?
2. Use cases     → What specific tasks do they need to accomplish?
3. Wireframes    → What structure and information hierarchy serves those tasks?
4. Visual design → What aesthetic treatment makes this trustworthy, clear, and on-brand?
```

Visual design is the last step, not the first. Each step constrains the next:

- Personas determine which use cases matter
- Use cases determine what content and actions appear on each screen
- Wireframes determine the structural hierarchy
- Visual design makes that hierarchy clear, trustworthy, and emotionally resonant

Skipping to visual design before wireframing produces screens that look good but don't serve the user's task. Skipping personas produces wireframes that serve the designer's assumptions, not the user's needs.

## Hammer vs. Shoe

A framework for right-sizing design investment:

- **Hammer:** A known solution looking for problems to solve. "We have a design system — let's apply it to everything." Hammers over-invest in areas that don't need it and under-invest in novel problems.
- **Shoe:** The right solution for a specific problem. "This signup flow has a 60% drop-off rate — let's understand why and fix it." Shoes match investment to impact.

Apply this to every design decision: is this investment justified by the problem it solves, or are we applying a familiar approach because we have it?

Examples:

- Building a full component library for a 3-page marketing site → hammer
- Redesigning the checkout flow that accounts for 80% of revenue → shoe
- Adding animations to every page transition → hammer
- Adding a loading skeleton to the dashboard that takes 3 seconds to load → shoe

## SEO as Design

Search results are a design surface. How a product appears in search results is often the first visual impression.

| Element               | Design Implication                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Title tag**         | Strongest on-page ranking signal. Write it like a headline — concise, specific, keyword-front-loaded. 50–60 characters         |
| **Meta description**  | Not a ranking factor, but determines click-through rate. ~155–160 characters. Write it like ad copy: what will the user get?   |
| **URL structure**     | Human-readable URLs signal quality to both users and search engines. `/pricing` not `/page?id=47`                              |
| **Heading hierarchy** | Semantic HTML (H1 → H2 → H3) structures content for both screen readers and search engines. One H1 per page                    |
| **Alt text**          | Descriptive alt text on images serves accessibility AND image search. Describe what's in the image, not what the page is about |
| **Structured data**   | Schema.org markup produces rich results (ratings, prices, FAQs). The SERP listing itself becomes a designed surface            |

These are not SEO hacks — they're design decisions about how the product presents itself before users even reach the site.
