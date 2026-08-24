/**
 * CategoryPage — the resolver.
 *
 * Route stays /category/:slug (and /shop), so every existing URL keeps working.
 * All this file does is: load the catalog through the shared engine, look up the
 * category's visual world, and hand both to that world.
 *
 * A slug with no configured world — or one whose world is not built yet — falls
 * through to DefaultWorld. This page never 404s a real category and never
 * invents one.
 */
import { useParams, useSearchParams } from "react-router-dom";
import { useCatalog } from "@/commerce/useCatalog";
import { worldFor } from "@/worlds/registry";
import DefaultWorld from "@/worlds/DefaultWorld";
import FashionWorld from "@/worlds/FashionWorld";
import JewelleryWorld from "@/worlds/JewelleryWorld";
import BeautyWorld from "@/worlds/BeautyWorld";
import LifestyleWorld from "@/worlds/LifestyleWorld";
import TechLifestyleWorld from "@/worlds/TechLifestyleWorld";
import KidsWorld from "@/worlds/KidsWorld";
import DigitalWorld from "@/worlds/DigitalWorld";

/** Built worlds. A configured slug with no entry here falls back to DefaultWorld. */
const WORLD_COMPONENTS = {
  FashionWorld,
  JewelleryWorld,
  BeautyWorld,
  LifestyleWorld,
  TechLifestyleWorld,
  KidsWorld,
  DigitalWorld,
};

export default function CategoryPage() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const search = params.get("search");

  const catalog = useCatalog(slug, search);
  const config = worldFor(slug);

  // A search query is a cross-category result set, so it always uses the
  // neutral presentation rather than one category's visual world.
  const World = !search && config.implemented ? WORLD_COMPONENTS[config.world] : null;

  // Worlds render their own composition and assume products exist, so the
  // shared loading / error / empty states are handled here first.
  if (World && !catalog.loading && !catalog.error && !catalog.isEmpty) {
    return <World catalog={catalog} config={config} />;
  }

  return <DefaultWorld catalog={catalog} search={search} />;
}
