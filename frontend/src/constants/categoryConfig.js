import {
  Shield,
  Landmark,
  Globe2,
  Factory,
  FlaskConical,
  Users,
  Trophy,
} from "lucide-react";

export const CATEGORY_CONFIG = [
  {
    name: "Defence & Security",
    short: "DEFENCE",
    icon: Shield,
    color: "cyan",
  },
  {
    name: "National Affairs",
    short: "NATIONAL",
    icon: Landmark,
    color: "blue",
  },
  {
    name: "International Affairs",
    short: "INTERNATIONAL",
    icon: Globe2,
    color: "blue",
  },
  {
    name: "Economy & Industry",
    short: "ECONOMY",
    icon: Factory,
    color: "amber",
  },
  {
    name: "Science & Technology",
    short: "SCIENCE",
    icon: FlaskConical,
    color: "green",
  },
  {
    name: "Society & Public Policy",
    short: "SOCIETY",
    icon: Users,
    color: "blue",
  },
  {
    name: "Sports & Culture",
    short: "SPORTS",
    icon: Trophy,
    color: "green",
  },
];

export const REVIEW_LIMIT = 50;
