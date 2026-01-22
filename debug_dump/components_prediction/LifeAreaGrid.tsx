import { LifeAreaCard } from "./LifeAreaCard";

export function LifeAreaGrid({ lifeAreas }: { lifeAreas: any }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Object.entries(lifeAreas).map(([key, v]: any) => (
        <LifeAreaCard
          key={key}
          title={key.replace("_", " ")}
          score={v.score}
          confidence={v.confidence}
        />
      ))}
    </div>
  );
}
