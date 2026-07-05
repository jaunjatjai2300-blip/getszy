import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export function CategoryCard({ category, large = false }) {
  return (
    <Link to={`/category/${category.slug}`} className={`group relative overflow-hidden rounded-2xl ${large ? "col-span-2 row-span-2 aspect-square sm:aspect-[1.2/1]" : "aspect-square"}`} data-testid={`category-card-${category.slug}`}>
      <img src={category.image} alt={category.name} className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy"/>
      <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(27,26,24,0.55) 100%)" }}/>
      <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
        <div className={`font-display ${large ? "text-2xl sm:text-3xl" : "text-lg"}`}>{category.name}</div>
        <div className="text-xs sm:text-sm opacity-90 flex items-center gap-1 mt-1">
          {category.product_count || 0} items <ArrowRight className="h-3 w-3"/>
        </div>
      </div>
    </Link>
  );
}
