# Campaign Portfolio Website - Project Plan

## Project Overview
A React-based campaign website focused on police accountability during protests, featuring a clean grid layout of officer profiles with detailed information and sources.

## Component Structure

### Main Components
1. **App.js** - Main application component with routing
2. **Header.js** - Navigation header with menu items
3. **HomePage.js** - Main grid layout page
4. **OfficerCard.js** - Individual officer card in grid
5. **OfficerProfile.js** - Detailed profile modal/page
6. **StaticPages.js** - Our Story, What We Want, About, Terms, Privacy

### Data Structure for Officer Profiles
```javascript
{
  id: string,
  badgeNumber: string,
  photo: string, // URL to square mugshot-style photo
  protestDate: string,
  location: string,
  role: string, // PSU, Liaison, Evidence gatherer, etc.
  notes: string, // Description of actions
  sources: [
    {
      type: string, // video, tweet, photo, article
      url: string,
      description: string
    }
  ]
}
```

## Routing Structure
- `/` - Home page with officer grid
- `/officer/:id` - Individual officer profile (if using pages instead of modal)
- `/our-story` - Campaign story page
- `/what-we-want` - Goals and demands page
- `/about` - About the campaign
- `/terms` - Terms of service
- `/privacy` - Privacy policy

## Design System
- **Colors**: Clean, professional palette with strong contrast
- **Typography**: Clear, readable fonts with proper hierarchy
- **Layout**: CSS Grid for officer cards, responsive design
- **Cards**: Rounded corners, subtle shadows, hover effects
- **Branding**: Social justice campaign aesthetic

## Technical Stack
- React 18
- Tailwind CSS for styling
- React Router for navigation
- Responsive design for mobile/desktop
- Modal or page-based profile views

