// Builds presentation/FPPVS-final-presentation.pptx from the experiment results.
// Run from presentation/build:  node build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "report", "figures");
const OUT = path.join(ROOT, "presentation", "FPPVS-final-presentation.pptx");
const SKILL = process.env.PPTX_SKILL_DIR;
const results = JSON.parse(fs.readFileSync(path.join(ROOT, "output", "scenarios", "scenario-results.json"), "utf8"));
const S = results.summary;
const acc = (key, m) => +(100 * S[key].methods[m].acceptance.mean).toFixed(1);
const val = (key, m, metric) => +S[key].methods[m][metric].mean.toFixed(1);

const THEME = {
  name: "FPPVS Network",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1A1A", lt1: "FFFFFF", dk2: "14213D", lt2: "EEF2F7",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "EDA100",
    accent5: "E87BA4", accent6: "008300", hlink: "2A78D6", folHlink: "6250D6",
  },
};
// Hex copies for chart options, which do not accept scheme colors.
const HEX = { ours: "2A78D6", original: "EB6834", spshare: "1BAF7A", spff: "EDA100", greedy: "E87BA4", random: "008300",
  ink: "1A1A1A", muted: "52514E", grid: "E4E3DF", navy: "14213D", tint: "EEF2F7" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "FPPVS: Implementation, Limitations and Modifications";
pres.author = "23CSB0B03, 23CSB0B17, 23CSB0B23, 23CSB0B56";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6;

// ---- layouts ---------------------------------------------------------------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: HEX.navy },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: W - 2 * M, h: 1.9, fontSize: 40, bold: true, color: "FFFFFF", fontFace: THEME.headFontFace, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.1, w: W - 2 * M, h: 1.6, fontSize: 18, color: "CADCFC", fontFace: THEME.bodyFontFace, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: 9.7, h: 0.95, fontSize: 28, bold: true, color: HEX.navy, fontFace: THEME.headFontFace, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "FPPVS | Advanced Computer Networks", options: { x: M, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: HEX.muted, fontFace: THEME.bodyFontFace, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
});

// ---- helpers ---------------------------------------------------------------
const presenters = ["23CSB0B03", "23CSB0B17", "23CSB0B23", "23CSB0B56"];
const sections = ["Introduction and the original paper", "What went wrong and the system", "Our modifications", "Results and conclusion"];
let currentSection = "";
function content(sectionIndex, title, notes) {
  const sectionTitle = `Part ${sectionIndex + 1}: ${sections[sectionIndex]} (${presenters[sectionIndex]})`;
  if (sectionTitle !== currentSection) { pres.addSection({ title: sectionTitle }); currentSection = sectionTitle; }
  const slide = pres.addSlide({ masterName: "CONTENT", sectionTitle });
  slide.addText(title, { placeholder: "title" });
  slide.addText(`Presenter: ${presenters[sectionIndex]}`, { x: W - M - 2.3, y: 0.6, w: 2.3, h: 0.35, fontSize: 12, color: C.text2, align: "right", isTextBox: true, margin: 0, objectName: "presenter" });
  slide.addNotes(notes);
  return slide;
}
function text(slide, value, opts) { slide.addText(value, { isTextBox: true, color: C.text1, fontSize: 16, valign: "top", ...opts }); }
function bullets(slide, items, opts) {
  slide.addText(items.map((item, i) => ({ text: item, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { isTextBox: true, color: C.text1, fontSize: 16, valign: "top", paraSpaceAfter: 8, ...opts });
}
function numberBadge(slide, n, x, y, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color }, line: { color }, objectName: `badge-${n}` });
  slide.addText(String(n), { x, y, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", isTextBox: true, margin: 0 });
}
function card(slide, x, y, w, h, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: name });
}
function stat(slide, value, label, x, y, w, color) {
  slide.addText(value, { x, y, w, h: 1.0, fontSize: 48, bold: true, color, fontFace: THEME.headFontFace, isTextBox: true, margin: 0 });
  slide.addText(label, { x, y: y + 1.0, w, h: 0.75, fontSize: 14, color: C.text2, isTextBox: true, margin: 0, valign: "top" });
}
function image(slide, file, x, y, w, ratio, alt) {
  slide.addImage({ path: path.join(FIG, file), x, y, w, h: w / ratio, altText: alt });
}
const axis = () => ({
  catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" }, catAxisLineShow: false, valAxisLineShow: false,
  legendFontSize: 12, legendColor: HEX.ink,
});

const MAIN = ["backbone@0.5", "backbone@0.75", "backbone@1.0", "metro@0.5", "metro@0.75", "metro@1.0"];
const MAIN_LABELS = ["Backbone 0.5", "Backbone 0.75", "Backbone 1.0", "Metro 0.5", "Metro 0.75", "Metro 1.0"];
const fppvsMain = MAIN.map((k) => acc(k, "fppvs"));
const origMain = MAIN.map((k) => acc(k, "original"));
const gains = fppvsMain.map((v, i) => v - origMain[i]);
const meanGain = (gains.reduce((a, b) => a + b, 0) / gains.length).toFixed(1);
const minFppvs = Math.min(...fppvsMain).toFixed(1);

// ---- 1. title ----------------------------------------------------------------
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
s.addText("Fairness-aware and Parallelized SFC Placement with VNF Sharing", { placeholder: "title" });
s.addText([
  { text: "Implementation, limitations and modifications of FPPVS", options: { breakLine: true } },
  { text: "Advanced Computer Networks: final project presentation", options: { breakLine: true } },
  { text: "23CSB0B03  |  23CSB0B17  |  23CSB0B23  |  23CSB0B56" },
], { placeholder: "body" });
s.addNotes("Opening (23CSB0B03).\n- Greet the professor, give the project title.\n- One line: we implemented the FPPVS paper, found why it performed badly in practice, fixed it, and compared our version with the original.\n- Mention the four parts and who presents each.");

// ---- 2. roadmap ----------------------------------------------------------------
s = content(0, "Roadmap", "Roadmap (23CSB0B03).\n- Four parts, one per presenter.\n- Key result to remember: the original FPPVS accepted about 10% in our first implementation; our updated version accepts 81-99% in every main scenario.");
sections.forEach((name, i) => {
  const y = 1.7 + i * 1.25;
  card(s, M, y, W - 2 * M, 1.0, `roadmap-${i}`);
  numberBadge(s, i + 1, M + 0.3, y + 0.22, [C.accent1, C.accent2, C.accent3, C.accent6][i]);
  text(s, name, { x: M + 1.1, y: y + 0.12, w: 7.5, h: 0.45, fontSize: 20, bold: true, margin: 0 });
  text(s, ["Problem, original FPPVS and Algorithm 1", "First results, limitations, system architecture", "Problem changes, placement method, learning model", "Setup, results, comparison with the paper, conclusion"][i],
    { x: M + 1.1, y: y + 0.55, w: 7.5, h: 0.4, fontSize: 14, color: C.text2, margin: 0 });
  text(s, presenters[i], { x: W - M - 2.6, y: y + 0.28, w: 2.3, h: 0.45, fontSize: 16, color: C.text2, align: "right", margin: 0 });
});

// ---- 3. problem ------------------------------------------------------------------
s = content(0, "The problem: placing service chains at the edge", "Problem (23CSB0B03).\n- NFV turns middleboxes into software VNFs; a service is an ordered chain of VNFs (SFC).\n- In MEC the VNFs run on small edge data centers with limited compute, linked by limited-bandwidth links.\n- For each request we pick a data center for every VNF and route traffic between them.\n- Three hard limits: compute, link bandwidth, end-to-end latency. Requests arrive and leave over time, so this is an online, NP-hard problem.");
const chain = ["Source", "FW", "IDS", "NAT", "LB", "Dest."];
chain.forEach((name, i) => {
  const x = M + 0.1 + i * 2.05;
  const endpoint = i === 0 || i === chain.length - 1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.85, w: 1.55, h: 0.75, rectRadius: 0.1, fill: { color: endpoint ? C.background2 : C.accent1 }, line: { color: endpoint ? C.text2 : C.accent1 }, objectName: `chain-${name}` });
  s.addText(name, { x, y: 1.85, w: 1.55, h: 0.75, fontSize: 16, bold: true, align: "center", valign: "middle", color: endpoint ? C.text1 : C.background1, isTextBox: true, margin: 0 });
  if (i < chain.length - 1) s.addShape(pres.shapes.LINE, { x: x + 1.6, y: 2.22, w: 0.4, h: 0, line: { color: C.text2, width: 1.5, endArrowType: "triangle" }, objectName: `chain-arrow-${i}` });
});
text(s, "A service function chain (SFC): every packet passes through the VNFs in order", { x: M, y: 2.75, w: 12, h: 0.4, fontSize: 14, color: C.text2, margin: 0 });
[["Compute", "Each edge DC has only 10-20 units; every VNF instance uses some of it"], ["Bandwidth", "Traffic between VNFs on different DCs uses every link on the route"], ["Latency", "End-to-end delay along the chain must stay under 100-150 ms"]].forEach(([head, body], i) => {
  const x = M + i * 4.1;
  card(s, x, 3.6, 3.85, 2.6, `limit-${head}`);
  numberBadge(s, i + 1, x + 0.3, 3.85, [C.accent1, C.accent2, C.accent3][i]);
  text(s, head, { x: x + 1.05, y: 3.9, w: 2.6, h: 0.5, fontSize: 20, bold: true, margin: 0 });
  text(s, body, { x: x + 0.3, y: 4.6, w: 3.3, h: 1.4, fontSize: 15, margin: 0 });
});

// ---- 4. original FPPVS --------------------------------------------------------------
s = content(0, "The original FPPVS: four ideas", "Original paper (23CSB0B03).\n- Paper: Zhu, Li and Rezaeipanah, Computer Networks, 2026.\n- 1. Parallelization: monitors run beside the main chain, which cuts latency.\n- 2. VNF sharing: reuse live instances; an SQN-LSTM forecasts demand.\n- 3. Fairness: an alpha-fair utility over throughput; Jain's index is reported.\n- 4. Federated actor-critic: local CNN agents, FedAvg in the cloud, adaptive epsilon-greedy.\n- The paper reports 88.1% (backbone) and 75.9% (metro) acceptance.");
[["SFC parallelization", "Monitors (IDS, DPI) move to parallel branches; shapers keep their order"], ["VNF sharing", "Reuse live instances; SQN-LSTM forecasts demand per VNF type"], ["Fairness", "Alpha-fair utility so a few heavy flows cannot take everything"], ["Federated DRL", "CNN actor-critic agents per region, averaged with FedAvg"]].forEach(([head, body], i) => {
  const x = M + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.45;
  card(s, x, y, 5.95, 2.2, `idea-${i}`);
  numberBadge(s, i + 1, x + 0.3, y + 0.3, C.accent1);
  text(s, head, { x: x + 1.05, y: y + 0.32, w: 4.6, h: 0.5, fontSize: 20, bold: true, margin: 0 });
  text(s, body, { x: x + 1.05, y: y + 0.95, w: 4.6, h: 1.1, fontSize: 15, margin: 0 });
});
text(s, "Paper reports 88.1% (backbone) and 75.9% (metro) acceptance", { x: M, y: 6.5, w: 12, h: 0.4, fontSize: 14, italic: true, color: C.text2, margin: 0 });

// ---- 5. algorithm 1 ------------------------------------------------------------------
s = content(0, "Algorithm 1: from a sequential to a parallel chain", "Algorithm 1 (23CSB0B03).\n- Shapers change packets, so their order is kept on the main chain.\n- Monitors only read packets, so they can run in parallel on a branch.\n- The dependency matrix says where a branch must rejoin: here IDS must finish before NAT.\n- DPI has no dependent shaper, so it rejoins at the destination.\n- Latency is then measured on the longest path of this graph (the critical path).\n- This figure is produced by our own implementation.");
image(s, "psfc-example.png", M + 0.6, 1.55, 10.8, 1800 / 720, "Sequential chain FW, IDS, DPI, NAT, LB converted into a main chain with IDS and DPI on parallel branches");
bullets(s, ["Shapers (orange) stay in order; monitors (green) run on branches", "IDS must finish before NAT; DPI rejoins at the destination", "Latency = longest path in this graph"], { x: M, y: 5.95, w: 12, h: 0.95, fontSize: 15 });

// ---- 6. first results ------------------------------------------------------------------
s = content(1, "Our first implementation accepted only 10%", "First results (23CSB0B17).\n- We first built the paper as written in Python.\n- Trained FDRL accepted 10.4% of requests, worse than greedy (15.8%) and random (11.6%).\n- Diagnosis: every single rejection was a link running out of bandwidth.\n- This told us the problem was not difficulty; something in the design and specification was wrong.");
stat(s, "10.4%", "Trained FDRL acceptance (original implementation)", M, 1.7, 3.6, C.accent2);
stat(s, "15.8%", "Greedy placement", M + 4.2, 1.7, 3.6, C.text2);
stat(s, "11.6%", "Random placement", M + 8.4, 1.7, 3.6, C.text2);
card(s, M, 4.1, W - 2 * M, 2.4, "diagnosis");
text(s, "Diagnosis", { x: M + 0.35, y: 4.3, w: 4, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["100% of rejections: link bandwidth exhausted", "VNFs were scattered over many DCs, so every chain crossed many links", "The learned policy did worse than random, so the model was not learning anything useful"], { x: M + 0.35, y: 4.9, w: W - 2 * M - 0.7, h: 1.5, fontSize: 16 });

// ---- 7. limitations ------------------------------------------------------------------
s = content(1, "Limitations of the original work", "Limitations (23CSB0B17).\n- L1: arrival rate not given; 1 per time unit with lifetime 1000 means ~1000 active chains, the network holds ~70-100.\n- L2: datasets, code and baseline settings not public.\n- L3: only compute is pruned; bandwidth and latency fail at the end of the chain.\n- L4: sharing capacity not defined; our first version overbooked.\n- L5: global pooling in the CNN loses which column is which DC.\n- L6: one request per episode; L7: no resources-per-service metric.\n- Green = fixed by us, orange = partly.");
const limits = [
  ["L1", "Arrival rate not specified; workload exceeds capacity", "Fixed"],
  ["L2", "Datasets, code and baseline settings not public", "Partly"],
  ["L3", "Only compute checked; bandwidth/latency fail at the end", "Fixed"],
  ["L4", "Sharing model can overbook capacity", "Fixed"],
  ["L5", "CNN cannot tell data centers apart", "Fixed"],
  ["L6", "One request per episode: no long-term view", "Partly"],
  ["L7", "No resources-per-service metric", "Fixed"],
];
const limitRows = [[
  { text: "", options: { bold: true, color: C.background1, fill: { color: C.text2 } } },
  { text: "Limitation", options: { bold: true, color: C.background1, fill: { color: C.text2 } } },
  { text: "Our status", options: { bold: true, color: C.background1, fill: { color: C.text2 } } },
]].concat(limits.map(([id, desc, status]) => [
  { text: id, options: { bold: true } }, { text: desc },
  { text: status, options: { bold: true, color: status === "Fixed" ? C.accent6 : C.accent2 } },
]));
s.addTable(limitRows, { x: M, y: 1.55, w: W - 2 * M, colW: [0.8, 9.3, 2.03], fontSize: 15, color: C.text1, border: { type: "solid", pt: 0.75, color: HEX.grid }, rowH: 0.6, valign: "middle", objectName: "limitations-table" });

// ---- 8. architecture ------------------------------------------------------------------
s = content(1, "System architecture", "Architecture (23CSB0B17).\n- Request types: 5 VNF types (IDS, DPI, LB, FW, NAT); sequential, parallel and mixed chains of 4-10 VNFs.\n- Flow: request -> Algorithm 1 -> state builder -> feasibility mask -> policy picks a DC -> admission check against the resource ledger.\n- Output per request: accept or reject, DC for each VNF, routes, latency breakdown, resources, reused instances.\n- Four local agents train on their own request streams and share only model weights.\n- Colours: blue = paper idea kept, orange = re-implemented, green = changed or added by us.");
image(s, "architecture.png", (W - 9.4) / 2, 1.4, 9.4, 2200 / 1240, "System architecture: cloud FedAvg server, four local agents, and the per-request placement pipeline");

// ---- 9. modified formulation ------------------------------------------------------------------
s = content(2, "What we changed in the problem", "Modified formulation (23CSB0B23).\n- M1: arrivals are a Poisson process; the rate comes from a stated offered load rho = offered compute / total capacity. We test 0.5, 0.75, 1.0, plus 1.25 and 1.5 as overload.\n- M2: every live VNF instance costs a fixed overhead (0.25) plus the demand of its flows; a shared instance pays the overhead once; everything counts against real capacity, so nothing is overbooked.\n- M4: the main objective is still acceptance; second objective is resources held per accepted service over time.");
[["Explicit load (M1)", "Poisson arrivals at a stated offered load: rho = offered compute / total capacity", "rho = 0.5, 0.75, 1.0 (+1.25, 1.5 overload)"],
 ["Honest sharing (M2)", "Each live instance costs 0.25 + demand of its flows; shared instance pays overhead once", "No overbooking of capacity"],
 ["Resource-time metric (M4)", "Second objective: resources held per accepted service over its lifetime", "Lower = cheaper to run"]].forEach(([head, body, foot], i) => {
  const x = M + i * 4.1;
  card(s, x, 1.6, 3.85, 4.9, `change-${i}`);
  numberBadge(s, i + 1, x + 0.3, 1.9, C.accent3);
  text(s, head, { x: x + 0.3, y: 2.65, w: 3.3, h: 0.9, fontSize: 20, bold: true, margin: 0 });
  text(s, body, { x: x + 0.3, y: 3.6, w: 3.3, h: 1.8, fontSize: 15, margin: 0 });
  text(s, foot, { x: x + 0.3, y: 5.55, w: 3.3, h: 0.8, fontSize: 14, italic: true, color: C.text2, margin: 0 });
});

// ---- 10. placement method ------------------------------------------------------------------
s = content(2, "How one placement decision works", "Placement method (23CSB0B23).\n- VNFs are placed one at a time in order; when a VNF is placed, every link into it can already be routed.\n- So before choosing a DC we check compute, bandwidth on the new links, and a latency lower bound. DCs that fail are masked.\n- The score is the network's logit plus a placement prior: keep the chain on few DCs, head towards the destination, reuse instances, avoid nearly full DCs and links.\n- If the chain still dead-ends, nothing has been committed yet, so we retry from up to 4 other first DCs before rejecting.");
image(s, "placement-flow.png", M + 0.6, 1.45, 10.8, 2000 / 680, "Placement decision flow: route, mask, score, pick, retry");
[["Look-ahead mask", "compute + bandwidth + latency checked before choosing"], ["Placement prior", "short chains, few DCs, reuse, avoid full links"], ["Rollback and retry", "up to 4 other first DCs before rejecting"]].forEach(([head, body], i) => {
  const x = M + i * 4.1;
  text(s, head, { x, y: 5.4, w: 3.85, h: 0.45, fontSize: 18, bold: true, color: C.accent3, margin: 0 });
  text(s, body, { x, y: 5.85, w: 3.85, h: 0.8, fontSize: 15, margin: 0 });
});

// ---- 11. learning model ------------------------------------------------------------------
s = content(2, "Learning model and training", "Learning model (23CSB0B23).\n- State: 9 features per DC column (5 added by us: latency to destination, bandwidth margin, reuse available, prior score, mask).\n- Network: the paper's 3 conv layers kept, but the actor scores each DC column with shared weights, so it can tell DCs apart; a learnable weight adds the prior.\n- Reward: +1 valid, -1 new instance, -10 rejected, small bandwidth penalty, final reward for latency slack plus a fairness bonus.\n- Training: advantage actor-critic, 4 federated agents x 10 rounds x 50 episodes, experience-weighted FedAvg, about 72 s per model on a laptop CPU.");
card(s, M, 1.55, 5.95, 4.95, "model-card");
text(s, "Network", { x: M + 0.35, y: 1.75, w: 5, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["State: 9 features per DC (5 added by us)", "3 conv layers x 64 filters, as in the paper", "Actor scores each DC with shared weights", "Logits + learnable weight x prior", "Critic: pooling, 256-unit layer, dropout 0.3"], { x: M + 0.35, y: 2.35, w: 5.3, h: 4.0, fontSize: 18 });
card(s, M + 6.15, 1.55, 5.95, 4.95, "training-card");
text(s, "Training", { x: M + 6.5, y: 1.75, w: 5, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["Advantage actor-critic, Adam (lr 5e-4)", "4 agents x 10 rounds x 50 episodes", "Experience-weighted FedAvg", "Reward: +1 valid, -1 new instance, -10 reject, + latency slack + fairness", "About 72 s per model on a laptop CPU"], { x: M + 6.5, y: 2.35, w: 5.3, h: 4.0, fontSize: 18 });

// ---- 12. setup ------------------------------------------------------------------
s = content(3, "Experimental setup", "Setup (23CSB0B56).\n- Hardware: Intel i5-12500H, 16 GB RAM, Windows 11, CPU only. Python 3.12, PyTorch 2.10, NetworkX.\n- Two topologies with the paper's sizes; parameter ranges from the paper's Section 5.1.\n- 5 seeds per scenario; each seed has a new network, training streams and a 600-request hold-out stream never used in training.\n- Load = offered compute demand / total capacity. 0.5-1.0 are the main scenarios, 1.25 and 1.5 are overload stress tests.");
const setupRows = [
  ["Topologies", "Backbone (24 DCs, 47 links), Metro (17 DCs, 29 links)"],
  ["Load levels", "0.5, 0.75, 1.0 (main); 1.25, 1.5 (overload)"],
  ["Requests", "4-10 VNFs, 5 types, rate 5-30, max latency 100-150 ms"],
  ["Capacities", "DC 10-20 units, links 100-200 units, latency 5-20 ms"],
  ["Repetitions", "5 seeds; 600 unseen test requests per run"],
  ["Training", "2000 episodes for every learning method"],
  ["Hardware", "Intel i5-12500H, 16 GB RAM, CPU only"],
].map(([k, v]) => [{ text: k, options: { bold: true } }, { text: v }]);
s.addTable(setupRows, { x: M, y: 1.6, w: W - 2 * M, colW: [2.6, 9.53], fontSize: 16, color: C.text1, border: { type: "solid", pt: 0.75, color: HEX.grid }, rowH: 0.62, valign: "middle", objectName: "setup-table" });

// ---- 13. methods compared ------------------------------------------------------------------
s = content(3, "Five methods, same scenarios", "Methods (23CSB0B56).\n- All five run in the same simulator, on the same networks and the same test requests.\n- Original FPPVS: run exactly as the paper specifies (4-row state, compute-only pruning, paper's CNN and reward, federated training).\n- 2022 adaptation (Zhang et al., JKSUCIS 2022): sequential placement, reuse of same-type VNFs, SQN-LSTM with TD = 20, actor-critic policy, rollback, LTCR reward. We implemented it from the method description; the authors' code is not available.\n- Greedy and random use our feasibility mask, so they never pick a DC already known to be infeasible.");
const methods = [
  ["Updated FPPVS (ours)", "Look-ahead mask, placement prior, honest sharing, retry, federated actor-critic", HEX.ours],
  ["Original FPPVS", "As the paper specifies: compute-only pruning, paper CNN and reward", HEX.original],
  ["2022 adaptation", "Zhang et al.: sequential chain, VNF reuse, SQN-LSTM (TD = 20), LTCR reward, rollback", HEX.spshare],
  ["Greedy", "Feasible DC with the most free compute, no sharing", HEX.spff],
  ["Random", "Any feasible DC, no sharing", HEX.greedy],
];
methods.forEach(([name, body, color], i) => {
  const y = 1.55 + i * 1.02;
  card(s, M, y, W - 2 * M, 0.88, `method-${i}`);
  s.addShape(pres.shapes.OVAL, { x: M + 0.3, y: y + 0.24, w: 0.4, h: 0.4, fill: { color }, line: { color }, objectName: `method-dot-${i}` });
  text(s, name, { x: M + 0.95, y: y + 0.2, w: 3.6, h: 0.5, fontSize: 18, bold: true, margin: 0 });
  text(s, body, { x: M + 4.6, y: y + 0.2, w: 7.3, h: 0.55, fontSize: 15, margin: 0 });
});

// ---- 14. acceptance chart ------------------------------------------------------------------
const zhangMain = MAIN.map((k) => acc(k, "zhang2022"));
s = content(3, "Acceptance: above 70% in every main scenario", `Acceptance (23CSB0B56).\n- Updated FPPVS is best in every scenario: ${minFppvs}-${Math.max(...fppvsMain).toFixed(1)}% in all six main scenarios; the lowest single seed was 77.5%.\n- Original FPPVS: ${Math.min(...origMain).toFixed(1)}-${Math.max(...origMain).toFixed(1)}%. 2022 adaptation: ${Math.min(...zhangMain).toFixed(1)}-${Math.max(...zhangMain).toFixed(1)}%, and it is the least stable (seed spread up to 15 points).\n- Greedy and random: 52-73%. They often beat the two learning baselines because they use our feasibility mask; the learning baselines only check compute and fail at the end of the chain.\n- The dashed line is the 70% target.`);
s.addChart([
  { type: pres.charts.BAR, data: [
    { name: "Updated FPPVS (ours)", labels: MAIN_LABELS, values: fppvsMain },
    { name: "Original FPPVS", labels: MAIN_LABELS, values: origMain },
    { name: "2022 adaptation", labels: MAIN_LABELS, values: zhangMain },
    { name: "Greedy", labels: MAIN_LABELS, values: MAIN.map((k) => acc(k, "greedy")) },
    { name: "Random", labels: MAIN_LABELS, values: MAIN.map((k) => acc(k, "random")) },
  ], options: { barDir: "col", barGrouping: "clustered", chartColors: [HEX.ours, HEX.original, HEX.spshare, HEX.spff, HEX.greedy], barGapWidthPct: 60 } },
  { type: pres.charts.LINE, data: [{ name: "70% target", labels: MAIN_LABELS, values: MAIN.map(() => 70) }],
    options: { chartColors: [HEX.ink], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none" } },
], { x: M, y: 1.45, w: 9.0, h: 5.35, ...axis(), showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20, valAxisTitle: "Acceptance (%)", showValAxisTitle: true, valAxisTitleFontSize: 12, valAxisTitleColor: HEX.muted, objectName: "acceptance-chart" });
stat(s, `${minFppvs}%`, "lowest main-scenario mean (Metro, load 1.0)", M + 9.4, 1.8, 2.75, C.accent1);
stat(s, "77.5%", "lowest single seed", M + 9.4, 4.0, 2.75, C.accent1);

// ---- 15. learning methods across load ------------------------------------------------------------------
const loads = ["0.5", "0.75", "1.0", "1.25", "1.5"];
const avgAcc = (m) => loads.map((l) => +(((acc(`backbone@${l}`, m) + acc(`metro@${l}`, m)) / 2).toFixed(1)));
const zgains = fppvsMain.map((v, i) => v - zhangMain[i]);
const meanZGain = (zgains.reduce((a, b) => a + b, 0) / zgains.length).toFixed(1);
s = content(3, "Updated vs original FPPVS vs 2022 adaptation", `Learning methods (23CSB0B56).\n- Average of Backbone and Metro at each load; same training budget, same test requests.\n- Updated FPPVS is ${meanGain} points above the original and ${meanZGain} above the 2022 adaptation on average in the main scenarios.\n- Why the other two fail: original FPPVS rejections are 80-86% bandwidth and 14-19% latency; 2022 adaptation 65-71% bandwidth and 28-35% latency. All of these are found only after the whole chain is placed, because both check compute only.\n- The 2022 adaptation has more latency failures because it does not parallelize monitors.\n- Above load 1.0 demand exceeds capacity and every method drops; ours stays ahead.`);
s.addChart(pres.charts.LINE, [
  { name: "Updated FPPVS (ours)", labels: loads, values: avgAcc("fppvs") },
  { name: "Original FPPVS", labels: loads, values: avgAcc("original") },
  { name: "2022 adaptation", labels: loads, values: avgAcc("zhang2022") },
], { x: M, y: 1.45, w: 8.4, h: 5.35, ...axis(),
  chartColors: [HEX.ours, HEX.original, HEX.spshare], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 8,
  showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20, catAxisTitle: "Offered load (1.0 = demand equals capacity)", showCatAxisTitle: true,
  catAxisTitleFontSize: 12, catAxisTitleColor: HEX.muted, valAxisTitle: "Acceptance (%)", showValAxisTitle: true, valAxisTitleFontSize: 12, valAxisTitleColor: HEX.muted, objectName: "learning-methods-chart" });
stat(s, `+${meanGain}`, "points vs original FPPVS (main-scenario average)", M + 8.8, 1.8, 3.4, C.accent1);
stat(s, `+${meanZGain}`, "points vs 2022 adaptation (main-scenario average)", M + 8.8, 4.0, 3.4, C.accent1);

// ---- 16. vs paper ------------------------------------------------------------------
s = content(3, "Comparison with the paper's published numbers", "Paper comparison (23CSB0B56).\n- First number column: values printed in the FPPVS paper. The rest: our runs at full load (rho = 1).\n- Our run of the original specification reaches 43.6% / 49.7%, far below the paper's 88.1% / 75.9%. We could not reproduce the published values.\n- Likely reasons: unstated arrival rate, real datasets not public, the paper trains on about 400,000 placements vs our 2,000, and some details are not fully specified.\n- Latency and utilization are defined differently, so those rows show trends only.\n- Updated FPPVS (86.4% / 81.3%) lands in the same range as the paper's published values.");
const pct = (k) => (x) => (100 * x[k].mean).toFixed(1);
const ms = (x) => x.mean_latency.mean.toFixed(1);
const pRow = (topo, metric, published, key, fmt) => {
  const [o, z, u] = ["original", "zhang2022", "fppvs"].map((m) => fmt(S[key].methods[m]));
  return [{ text: topo, options: { bold: true } }, { text: metric }, { text: String(published) }, { text: o }, { text: z }, { text: u, options: { bold: true, color: C.accent1 } }];
};
const head = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, align: "center" } });
s.addTable([
  [head("Topology"), head("Metric"), head("Paper: FPPVS"), head("Ours: original"), head("Ours: 2022"), head("Ours: updated")],
  pRow("Backbone", "Acceptance (%)", 88.1, "backbone@1.0", pct("acceptance")),
  pRow("", "Latency (ms)", 134.4, "backbone@1.0", ms),
  pRow("", "Utilization (%)", 75.35, "backbone@1.0", pct("compute_utilization")),
  pRow("Metro", "Acceptance (%)", 75.9, "metro@1.0", pct("acceptance")),
  pRow("", "Latency (ms)", 160.1, "metro@1.0", ms),
  pRow("", "Utilization (%)", 72.36, "metro@1.0", pct("compute_utilization")),
], { x: M, y: 1.55, w: W - 2 * M, colW: [1.7, 2.6, 1.95, 1.95, 1.95, 1.98], fontSize: 16, color: C.text1, align: "center", border: { type: "solid", pt: 0.75, color: HEX.grid }, rowH: 0.58, valign: "middle", objectName: "paper-table" });
text(s, "Different data, training budget and metric definitions: compare trends, not exact values. We could not reproduce the paper's 88.1% with its own specification.",
  { x: M, y: 5.85, w: W - 2 * M, h: 0.8, fontSize: 15, italic: true, color: C.text2, margin: 0 });

// ---- 17. resources ------------------------------------------------------------------
s = content(3, "Resources: least bandwidth per running service", "Resources (23CSB0B56).\n- Bandwidth held per running service is lowest for updated FPPVS in every main scenario.\n- About 57% less than greedy and random, 31% less than the original FPPVS, 14% less than the 2022 adaptation.\n- Compute: 14% less than greedy and random (no sharing there), but about 4% more than the original and 2022 methods. Those accept only about half the requests, most likely the easy ones, so their per-request averages come from an easier set.\n- New instances per accepted service: 0.5-0.9 for ours vs about 7 without sharing.");
s.addChart(pres.charts.BAR, [
  { name: "Updated FPPVS (ours)", labels: MAIN_LABELS, values: MAIN.map((k) => val(k, "fppvs", "bandwidth_per_active_sfc")) },
  { name: "Original FPPVS", labels: MAIN_LABELS, values: MAIN.map((k) => val(k, "original", "bandwidth_per_active_sfc")) },
  { name: "2022 adaptation", labels: MAIN_LABELS, values: MAIN.map((k) => val(k, "zhang2022", "bandwidth_per_active_sfc")) },
  { name: "Greedy", labels: MAIN_LABELS, values: MAIN.map((k) => val(k, "greedy", "bandwidth_per_active_sfc")) },
  { name: "Random", labels: MAIN_LABELS, values: MAIN.map((k) => val(k, "random", "bandwidth_per_active_sfc")) },
], { x: M, y: 1.45, w: 8.6, h: 5.35, ...axis(), barDir: "col", barGrouping: "clustered", chartColors: [HEX.ours, HEX.original, HEX.spshare, HEX.spff, HEX.greedy], barGapWidthPct: 60,
  showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisTitle: "Bandwidth per running SFC (units)", showValAxisTitle: true, valAxisTitleFontSize: 12, valAxisTitleColor: HEX.muted, objectName: "bandwidth-chart" });
stat(s, "-57%", "bandwidth vs greedy / random", M + 9.0, 1.7, 3.2, C.accent1);
stat(s, "-31%", "bandwidth vs original FPPVS", M + 9.0, 3.45, 3.2, C.accent1);
stat(s, "-14%", "bandwidth vs 2022 adaptation", M + 9.0, 5.2, 3.2, C.accent1);

// ---- 17. ablation ------------------------------------------------------------------
const ABL = [["fppvs", "Full"], ["no-sharing", "No sharing"], ["no-fairness", "No fairness"], ["single-agent", "1 agent"], ["no-retry", "No retry"], ["prior-only", "Prior only"]];
s = content(3, "What actually makes the difference", "Ablation (23CSB0B56).\n- Remove one part at a time, full load.\n- Sharing matters most: without it acceptance drops 9-13 points at load 0.75 and above.\n- Fairness, single vs federated, and retries each change about one point or less.\n- Honest finding: the prior alone, with no neural network, scores within about one point of the full method. Our gains come from the problem fixes (mask, sharing model, prior), not from reinforcement learning.\n- Reason: each episode is one request, so the agent sees little long-term effect (limitation L6). Future work: multi-request episodes.");
s.addChart(pres.charts.BAR, [
  { name: "Backbone, load 1.0", labels: ABL.map((a) => a[1]), values: ABL.map(([m]) => acc("backbone@1.0", m)) },
  { name: "Metro, load 1.0", labels: ABL.map((a) => a[1]), values: ABL.map(([m]) => acc("metro@1.0", m)) },
], { x: M, y: 1.45, w: 7.6, h: 5.35, ...axis(), barDir: "col", barGrouping: "clustered", chartColors: [HEX.ours, "6EA8E8"], barGapWidthPct: 50,
  showLegend: true, legendPos: "b", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.ink, dataLabelFormatCode: "0", objectName: "ablation-chart" });
card(s, M + 8.0, 1.55, 4.13, 5.0, "ablation-takeaways");
text(s, "Takeaways", { x: M + 8.3, y: 1.75, w: 3.6, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["Sharing: biggest effect (9-13 points)", "Fairness, agents, retry: about 1 point", "Prior only = full method within about 1 point", "Gains come from fixing the problem, not from the RL"], { x: M + 8.3, y: 2.35, w: 3.6, h: 4.0, fontSize: 18 });

// ---- 18. conclusion ------------------------------------------------------------------
s = content(3, "Conclusion and future work", "Conclusion (23CSB0B56).\n- Main message: the original FPPVS failed in practice mostly because of specification and design gaps, not because the problem is hopeless.\n- With a stated load, a look-ahead mask, honest sharing and a placement prior, acceptance goes from about 10% to 81-99% in every main scenario, with less bandwidth per service.\n- Limits: synthetic data, simplified baselines, and RL adds little on its own.\n- Future work: real datasets, re-implement the paper's baselines, multi-request episodes, VNF migration.");
card(s, M, 1.55, 5.95, 4.95, "conclusion-card");
text(s, "What we showed", { x: M + 0.35, y: 1.75, w: 5, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["Original FPPVS " + Math.min(...origMain).toFixed(0) + "-" + Math.max(...origMain).toFixed(0) + "%, 2022 adaptation " + Math.min(...zhangMain).toFixed(0) + "-" + Math.max(...zhangMain).toFixed(0) + "% on the same scenarios", "Updated: " + minFppvs + "-" + Math.max(...fppvsMain).toFixed(1) + "% in every main scenario", "Least bandwidth per running service of all five methods", "Honest about limits: synthetic data, our own 2022 adaptation, RL adds little"], { x: M + 0.35, y: 2.35, w: 5.3, h: 4.0, fontSize: 18 });
card(s, M + 6.15, 1.55, 5.95, 4.95, "future-card");
text(s, "Future work", { x: M + 6.5, y: 1.75, w: 5, h: 0.5, fontSize: 20, bold: true, margin: 0 });
bullets(s, ["Evaluate on the real USAnet and Italian operator data", "Re-implement RVNF, DRL-SFCP, PVFP and DPC", "Multi-request episodes so learning can beat the prior", "VNF migration to repack long-lived chains"], { x: M + 6.5, y: 2.35, w: 5.3, h: 4.0, fontSize: 18 });

// ---- 19. thank you ------------------------------------------------------------------
pres.addSection({ title: "Closing" });
s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Closing" });
s.addText("Thank you. Questions?", { placeholder: "title" });
s.addText("Code, report and all results: acn/ repository (scripts/run_scenarios.py reproduces every number)", { placeholder: "body" });
s.addNotes("Closing (23CSB0B56).\nLikely questions and short answers:\n- Why so much better than the original? The original checks only compute, so most chains fail at the last step on bandwidth or latency, and its network cannot tell DCs apart.\n- Is the workload change cheating? It is stated openly (L1, M1). On the original workload our placement still gets 70.4% vs 10.4%.\n- Why not the paper's baselines? Code and configurations are not public; we compared against the original FPPVS itself, a 2022 method we implemented from its description, greedy and random.\n- Is the 2022 comparison fair? Same simulator, same requests, same training budget; it is our implementation from the description, which we state openly.\n- Does the RL help? Honestly, very little; the prior does most of the work. That is our main future-work item.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
