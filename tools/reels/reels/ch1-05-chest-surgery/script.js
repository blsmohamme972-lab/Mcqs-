// Narration and metadata for reel 05. Facts: Chapter 1, p 2 of Cardiothoracic Surgery (2nd ed.).
// Note: Sentences 'why2' and 'report' give the purpose of the scan and report; the book states the items, not the purpose.
export const script = {
  id: "ch1-05-chest-surgery", index: 5, total: 18,
  title: "A previous operation changes the next one",
  kicker: "CV history · Redo", source: "Ch 1 · p 2",
  poster: { at: "ct", plus: 2.0 },
  sentences: [
    { id: "hook", text: "A previous operation / changes the next one." },
    { id: "find", text: "Find it three ways: / ask, / check the chart, / and look." },
    { id: "look", text: "Look carefully at the whole chest, / and the back, / for scars." },
    { id: "scar", text: "A scar is the quickest clue / when the history is vague." },
    { id: "risk", text: "Previous cardiac surgery / adds to operative mortality, / and needs several changes / to the standard approach." },
    { id: "incr", text: "That added risk is incremental, / on top of every other factor." },
    { id: "ct", text: "That is why most patients / should have a {CT=C T} of the chest." },
    { id: "why", text: "It shows how the aorta / and the right ventricle / sit behind the sternum." },
    { id: "graft", text: "And where the patent bypass grafts run." },
    { id: "why2", text: "Those relationships decide / how safely the chest can be reopened." },
    { id: "contrast", text: "The scan needs intravenous contrast." },
    { id: "report", text: "And always obtain the operative report: / it records what was done." },
    { id: "rec", text: "Scars. {CT=C T}. Contrast. Report." },
  ],
};
