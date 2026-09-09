# Frontend Component Architecture Guide

## Overview
The frontend has been refactored from a monolithic App.jsx into a modular, component-based architecture.

## Directory Structure

### `/components/Common/` - Reusable Components
- **Metric.jsx** - Displays metric cards with label, value, and detail
- **PageHeader.jsx** - Page title, description, and system status indicator  
- **SidebarItem.jsx** - Navigation button with icon, label, and optional count
- **ArticleCard.jsx** - Article display with category, title, summary, and metadata

### `/components/Layout/` - Layout Components
- **Sidebar.jsx** - Main navigation sidebar with all sections and menu items
  - Workspace navigation
  - Category navigation
  - Analysis section
  - Pipeline status footer
- **Topbar.jsx** - Top navigation bar with breadcrumb, search, and system controls

### `/components/Pages/` - Page Components
Each page component handles a specific view in the application:

- **OverviewPage.jsx**
  - Metrics grid (articles, categories, accuracy, review queue)
  - Category overview with clickable cards
  - System status panel

- **DigestPage.jsx**
  - Filtered article list by category
  - Empty state handling

- **CategoryPage.jsx**
  - Category-specific article view
  - Articles with confidence scores
  - Click-through capability

- **ReviewPage.jsx**
  - Low-confidence articles for human review
  - Ranked by confidence level
  - Quality assurance interface

- **LoadingState.jsx**
  - LoadingScreen component with spinner
  - ErrorScreen component with retry button

- **EvaluationPage.jsx** (placeholder)
  - Model performance metrics
  - Evaluation dashboard

### `/constants/` - Application Constants
- **categoryConfig.js**
  - CATEGORY_CONFIG array with category definitions
  - REVIEW_LIMIT constant

### `/utils/` - Helper Functions
- **helpers.js**
  - getPageTitle() - Convert page name to display title
  - getCategoryClass() - Get CSS class for category
  - getConfidenceClass() - Get confidence level class
  - formatTime() - Format timestamps

## Component Props Documentation

### PageHeader
```jsx
<PageHeader
  eyebrow="SECTION LABEL"
  title="Page Title"
  description="Page description text"
  systemOnline={boolean}
/>
```

### Metric
```jsx
<Metric
  label="LABEL"
  value={123}
  detail="Detail text"
  accent="cyan|green|amber|red"
/>
```

### SidebarItem
```jsx
<SidebarItem
  icon={IconComponent}
  label="Item Label"
  active={boolean}
  count={number}
  onClick={() => {}}
/>
```

### Sidebar
```jsx
<Sidebar
  activePage={string}
  onNavigate={(page) => {}}
  onCategory={(category) => {}}
  categoryCounts={{}}
  reviewCount={number}
  systemOnline={boolean}
  sidebarOpen={boolean}
  onClose={() => {}}
/>
```

## Responsive Breakpoints

- **Desktop**: Full layout with fixed sidebar
- **Tablet** (< 900px): Narrower sidebar, 2-column grid layouts
- **Mobile** (< 650px): 
  - Sidebar becomes slide-out drawer
  - Mobile menu button appears
  - Single column layouts
  - Optimized spacing

## Data Flow

1. **App.jsx** (main component)
   - Manages global state (activePage, articles, etc.)
   - Fetches data from API
   - Renders layout and page components
   
2. **Layout Components** (Sidebar, Topbar)
   - Receive navigation state and callbacks
   - Handle user interactions
   
3. **Page Components**
   - Receive filtered/processed data from App
   - Display content using Common components
   
4. **Common Components**
   - Purely presentational
   - No data fetching
   - Reusable across pages

## Styling

All styles are in `index.css` with:
- CSS custom properties for colors
- Flexbox for layout
- Mobile-first responsive design
- Smooth transitions and animations
- Semantic spacing system

## State Management

Currently using React hooks (useState, useEffect, useMemo):
- `activePage` - Current view
- `activeCategory` - Selected category filter
- `allArticles` - Full article dataset
- `categoryCounts` - Articles per category
- `systemOnline` - Pipeline status
- `loading` / `error` - API state

Future: Consider Redux/Zustand if state complexity increases.
