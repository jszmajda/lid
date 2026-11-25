// The research section's data: every entry in src/research/, newest first, each with its
// report rendered. LID_RESEARCH_DIR and LID_RESEARCH_TODAY let the tests build from fixtures.
// @spec ONB-RESEARCH-004, ONB-RESEARCH-010
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadReports } from "../../scripts/research-entries.js";

const srcDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const researchDir = () => process.env.LID_RESEARCH_DIR || join(srcDir, "research");

export default function () {
  const today = process.env.LID_RESEARCH_TODAY;
  const reports = loadReports(researchDir(), today ? { today } : {});
  return { reports };
}
