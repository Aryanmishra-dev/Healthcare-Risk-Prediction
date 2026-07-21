import forms from "@tailwindcss/forms";
import containerQueries from "@tailwindcss/container-queries";

/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./src/pages/templates/**/*.html",
        "./src/components/**/*.html",
    ],
    theme: {
        extend: {
            colors: {
                primary: "#0284c5",
                "background-light": "#f5f7f8",
            },
            fontFamily: {
                display: ["Inter", "sans-serif"],
            },
            borderRadius: {
                DEFAULT: "0.25rem",
                lg: "0.5rem",
                xl: "0.75rem",
                full: "9999px",
            },
        },
    },
    plugins: [forms, containerQueries],
};
