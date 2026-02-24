import { Box, Button, Typography } from "@mui/material";
import { MetadataFilters, SearchBar } from "../common";
import { useNavigate } from "react-router-dom";

const EXAMPLE_QUERIES = [
    "altitude deviation",
    "runway incursion",
    "ATC clearance",
];

export const Search = () => {
    const navigate = useNavigate();

    const onSubmit = () => {
        navigate("/results");
    };

    const runExample = (query) => {
        localStorage.setItem("user-query", query);
        navigate("/results");
    };

    return (
        <Box
            sx={{
                minHeight: "100dvh",
                position: "relative",
            }}
        >
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    textAlign: "center",
                    py: "20dvh",
                    px: 2,
                    mb: 1,
                }}
            >
                <Box sx={{ position: "absolute", top: 16, right: 16 }}>
                    <Button onClick={() => navigate("/about")}>About</Button>
                </Box>

                <Typography variant="h1" sx={{ fontSize: "30pt", mb: 1 }}>
                    Aviation Safety Search
                </Typography>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 480 }}>
                    Quick start: Enter a safety scenario or keywords, then review results. Use filters to narrow by date, location, or anomaly type.
                </Typography>

                <Box sx={{ py: 1, width: "100%", maxWidth: "40dvw" }}>
                    <SearchBar onSubmit={onSubmit} />
                </Box>

                <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                        Try an example:
                    </Typography>
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", justifyContent: "center" }}>
                        {EXAMPLE_QUERIES.map((q) => (
                            <Button key={q} variant="outlined" size="small" onClick={() => runExample(q)}>
                                {q}
                            </Button>
                        ))}
                    </Box>
                </Box>

                <Box sx={{ mt: 2 }}>
                    <MetadataFilters />
                </Box>
            </Box>
        </Box>
    );
};