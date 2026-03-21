import { Link, useLocation } from "wouter";
import { ThemeToggle } from "./theme-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sparkles, Activity, BookOpen, Settings, BookMarked, User, LogOut, BarChart2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export function Navigation() {
  const [location] = useLocation();
  const { user, logout } = useAuth();

  const navItems = [
    { href: "/", label: "Generate Chart", icon: Sparkles },
  ];

  const utilityItems = [
    { href: "/health", label: "Health Status", icon: Activity },
    { href: "/docs", label: "Documentation", icon: BookOpen },
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
          {user && (
            <Link href="/my-charts">
              <Button
                variant={location === "/my-charts" ? "secondary" : "ghost"}
                size="sm"
                className="gap-2"
              >
                <BookMarked className="h-4 w-4" />
                <span className="hidden md:inline">My Charts</span>
              </Button>
            </Link>
          )}
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

          {/* Auth area */}
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <User className="h-4 w-4" />
                  <span className="hidden md:inline max-w-[100px] truncate">{user.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-2 py-1.5">
                  <p className="text-xs font-medium truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/my-charts" className="flex items-center gap-2 cursor-pointer">
                    <BookMarked className="h-4 w-4" /> My Charts
                  </Link>
                </DropdownMenuItem>
                {user.role === "admin" && (
                  <>
                    <DropdownMenuItem asChild>
                      <Link href="/admin" className="flex items-center gap-2 cursor-pointer">
                        <BarChart2 className="h-4 w-4" /> Admin Dashboard
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href="/admin/llm" className="flex items-center gap-2 cursor-pointer">
                        <Settings className="h-4 w-4" /> LLM Settings
                      </Link>
                    </DropdownMenuItem>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="flex items-center gap-2 text-destructive focus:text-destructive cursor-pointer"
                  onClick={() => logout()}
                >
                  <LogOut className="h-4 w-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link href="/login">
              <Button variant="ghost" size="sm" className="gap-2">
                <User className="h-4 w-4" />
                <span className="hidden md:inline">Sign in</span>
              </Button>
            </Link>
          )}

          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
// cache bust Sat Mar 21 13:51:29 PDT 2026
