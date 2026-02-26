import { Box, Button, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

export const About = () => {
    const navigate = useNavigate();

    return (
        <Box
            sx={{
                maxWidth: 720,
                mx: "auto",
                px: 3,
                py: 4,
            }}
        >
            <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
                <Button onClick={() => navigate("/")}>Home</Button>
                <Button onClick={() => navigate("/results")}>Search</Button>
            </Box>

            <Typography variant="h4" component="h1" gutterBottom>
                About Aviation Safety Search
            </Typography>

            <Typography variant="body1" paragraph>
                This application is a search engine over the <strong>NASA Aviation Safety Reporting System (ASRS)</strong> database.
                It is designed for safety managers, analysts, and researchers who need to find relevant incident and voluntary reports quickly.
            </Typography>

            <Typography variant="h6" gutterBottom>
                How it works
            </Typography>
            <Typography variant="body1" paragraph>
                Enter a safety scenario or keywords (e.g. altitude deviation, runway incursion, ATC clearance).
                You can search with <strong>BM25</strong> (lexical) or <strong>Hybrid</strong> (BM25 + embeddings). Results are ranked by relevance.
                Use metadata filters to narrow by event date, location, and anomaly type. Matching terms in the narrative are highlighted.
            </Typography>

            <Typography variant="h6" gutterBottom>
                Data source
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
                Reports are from the public ASRS dataset. This tool is for research and analysis only; always verify with official sources when needed.
            </Typography>

            <Typography variant="body2" color="text.secondary">
                Built as a capstone project for MIDS. For methodology and setup, see the project documentation.
            </Typography>
        </Box>
    );
};
