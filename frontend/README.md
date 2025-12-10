# Research Paper Analyst - Frontend

A sleek, SaaS-style Next.js frontend for the Research Paper Analyst application.

## Features

- 🎨 Modern dark theme with teal/cyan accents
- ✨ Smooth animations with Framer Motion
- 📤 Drag-and-drop PDF upload
- 📊 Tabbed results interface
- 📱 Fully responsive design
- 🔗 Complete backend API integration

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend server running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env.local` file in the frontend directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css       # Design system & tokens
│   │   ├── layout.js         # Root layout
│   │   ├── page.js           # Landing page
│   │   └── analyze/
│   │       └── page.js       # Analysis page
│   ├── components/
│   │   ├── ui/               # Reusable UI components
│   │   ├── layout/           # Navbar, Footer
│   │   ├── features/         # Feature-specific components
│   │   └── animations/       # Lottie animation wrapper
│   └── lib/
│       ├── api.js            # Backend API client
│       ├── utils.js          # Utility functions
│       └── animations.js     # Lottie animation data
└── public/
```

## API Integration

The frontend connects to these backend endpoints:

| Endpoint                | Method | Description          |
| ----------------------- | ------ | -------------------- |
| `/api/uploads/`         | POST   | Upload PDF file      |
| `/api/analyze/`         | POST   | Run analysis on file |
| `/api/report/{file_id}` | GET    | Download PDF report  |

## Technologies

- **Next.js 14** - React framework
- **Framer Motion** - Animations
- **Lottie React** - Lottie animations
- **React Dropzone** - File uploads
- **Lucide React** - Icons
