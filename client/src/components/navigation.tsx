import { Link, useLocation } from "wouter";
import { ThemeToggle } from "./theme-toggle";
import { Button } from "@/components/ui/button";
import { Sparkles, Calendar, FileText, Activity, BookOpen, Settings } from "lucide-react";

export function Navigation() {
  const [location] = useLocation();

  const navItems = [
    { href: "/", label: "Generate Chart", icon: Sparkles },
/*    { href: "/predictions", label: "Monthly Predictions", icon: Calendar }, */
    { href: "/reports", label: "Reports", icon: FileText },
  ];

  
  const utilityItems = [
    { href: "/health", label: "Health Status", icon: Activity },
    { href: "/docs", label: "Documentation", icon: BookOpen },
    { href: "/admin/llm", label: "LLM Admin", icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between gap-4 max-w-7xl mx-auto px-4">
        <div className="flex items-center gap-2">
          <Link href="/" className="flex items-center gap-2" data-testid="link-home">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-serif font-semibold text-lg hidden sm:block">
              Tamil Panchangam
            </span>
          </Link>
        </div>

        <nav className="flex items-center gap-1 flex-wrap">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? "secondary" : "ghost"}
                  size="sm"
                  className="gap-2"
                  data-testid={`link-nav-${item.label.toLowerCase().replace(/\s/g, '-')}`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </Button>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-1">
          {utilityItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant="ghost"
                  size="icon"
                  title={item.label}
                  data-testid={`link-${item.label.toLowerCase().replace(/\s/g, '-')}`}
                >
                  <Icon className="h-4 w-4" />
                </Button>
              </Link>
            );
          })}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
