import { aggregateInterpretation } from "../utils/aggregateInterpretation";

export function InterpretationPanel({ interpretation }) {
  const summary = aggregateInterpretation(interpretation);


  return (
    <div className="rounded-xl bg-gray-50 p-5">
      <h4 className="font-semibold mb-2">Monthly Overview</h4>
      <p className="text-gray-700">{summary}</p>
    </div>
  );
}
