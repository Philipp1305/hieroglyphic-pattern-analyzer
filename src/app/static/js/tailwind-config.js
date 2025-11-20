tailwind.config = {
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "primary": "#E97451", // Burnt Sienna
                "background-light": "#F0F2F6",
                "background-dark": "#101922",
                "card-light": "#ffffff",
                "card-dark": "#182431",
                "text-light": "#31333F",
                "text-dark": "#EAECEF",
                "text-secondary-light": "#617589",
                "text-secondary-dark": "#98A3B2",
                "border-light": "#dbe0e6",
                "border-dark": "#313c4a",
            },
            fontFamily: {
                "display": ["Inter", "sans-serif"]
            },
            borderRadius: {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "9999px"
            },
        },
    },
}