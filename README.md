# AI Drawing Board

An interactive AI-powered Drawing Board that allows users to create sketches and drawings on a digital canvas. The application combines drawing functionality with AI capabilities to enhance creativity, provide intelligent assistance, and improve the user experience.

## Live Demo

Backend stream/API:

https://ai-drawing-board-1.onrender.com

Frontend deployment target:

`https://your-project-name.vercel.app`

## Features

- Interactive drawing canvas
- Freehand sketching
- Multiple brush sizes
- Color selection tools
- Canvas clear/reset option
- Real-time drawing experience
- AI-assisted drawing capabilities
- Responsive user interface

## Technologies Used

- HTML5
- CSS3
- JavaScript
- Canvas API
- AI/ML Integration (if applicable)
- FastAPI
- OpenCV
- MediaPipe

## Deployment Notes

This project is split into:

- `frontend/`: static UI, suitable for Vercel
- `backend/`: Python webcam processing server, suitable for Render or another long-running server host

Vercel should host only the frontend for this repo. The frontend is already configured to use the Render backend at:

`https://ai-drawing-board-1.onrender.com`

## Preview

![AI Drawing Board](screenshots/ai-drawing-board.png)


## Project Objectives

- Create a digital drawing environment.
- Explore HTML5 Canvas API.
- Implement interactive drawing features.
- Integrate AI-powered functionality.
- Enhance creativity through technology.

## Learning Outcomes

Through this project, I learned:

- Canvas API Fundamentals
- JavaScript Event Handling
- DOM Manipulation
- Interactive UI Design
- AI Integration Concepts
- Frontend Development Best Practices

## Workflow

```text
User Drawing
      ↓
Canvas Processing
      ↓
AI Analysis (Optional)
      ↓
Drawing Enhancement
      ↓
Output Display
```

## Future Enhancements

- Shape Recognition
- AI Sketch Suggestions
- Image Generation from Drawings
- Save and Export Drawings
- Undo/Redo Functionality
- Collaborative Drawing Board
- Dark Mode Support

## Applications

- Digital Art Creation
- Educational Tools
- Creative Design
- Sketch Prototyping
- AI-Assisted Learning
