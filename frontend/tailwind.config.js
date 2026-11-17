/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cuidacor-menta': '#E6F4F1',
        'cuidacor-turquesa': '#1C8C81',
        'cuidacor-rojo': '#D32F2F',
      }
    },
  },
  plugins: [],
}