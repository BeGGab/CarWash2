/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./admin-carwash.html",
    "./system-admin.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "wash-primary": "#0066FF",
        "wash-secondary": "#00D4AA",
        "wash-accent": "#FF6B00",
      },
    },
  },
  plugins: [],
};
