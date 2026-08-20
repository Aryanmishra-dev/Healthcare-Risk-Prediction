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
                primary: "#06B6D4",
                "brand-navy": "#0B0F19",
                "brand-rose": "#F43F5E",
                "brand-cyan": "#06B6D4",
                "background-light": "#F8FAFC",
            },
            fontFamily: {
                display: ["Outfit", "sans-serif"],
                body: ["Manrope", "sans-serif"],
                mono: ["Geist Mono", "monospace"],
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
