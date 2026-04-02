import { Box, Button, FormControl, FormControlLabel, InputLabel, MenuItem, Paper, Select, Switch, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { MetadataFilters, SearchBar } from "../common";
import { useNavigate } from "react-router-dom";

const SEARCH_MODE_KEY = "search-mode";
const USE_QE_KEY = "use-qe";
const USE_QE_JUDGE_KEY = "use-qe-judge";

const EXAMPLE_QUERIES = [
    "altitude deviation",
    "runway incursion",
    "ATC clearance",
];

export const Search = () => {
    const navigate = useNavigate();
    const [searchMode, setSearchMode] = useState(localStorage.getItem(SEARCH_MODE_KEY) || "bm25");
    const [useQe, setUseQe] = useState(localStorage.getItem(USE_QE_KEY) === "true");
    const [useQeJudge, setUseQeJudge] = useState(localStorage.getItem(USE_QE_JUDGE_KEY) === "true");

    useEffect(() => {
        localStorage.setItem(SEARCH_MODE_KEY, searchMode);
    }, [searchMode]);

    useEffect(() => {
        localStorage.setItem(USE_QE_KEY, String(useQe));
    }, [useQe]);

    useEffect(() => {
        localStorage.setItem(USE_QE_JUDGE_KEY, String(useQeJudge));
    }, [useQeJudge]);

    const onToggleQe = (checked) => {
        setUseQe(checked);
        if (!checked) {
            setUseQeJudge(false);
        }
    };

    const onSubmit = () => {
        localStorage.setItem(SEARCH_MODE_KEY, searchMode);
        localStorage.setItem(USE_QE_KEY, String(useQe));
        localStorage.setItem(USE_QE_JUDGE_KEY, String(useQeJudge));
        navigate("/results");
    };

    const runExample = (query) => {
        localStorage.setItem("user-query", query);
        localStorage.setItem(SEARCH_MODE_KEY, searchMode);
        localStorage.setItem(USE_QE_KEY, String(useQe));
        localStorage.setItem(USE_QE_JUDGE_KEY, String(useQeJudge));
        navigate("/results");
    };

    return (
        <Box
            sx={{
                minHeight: "100dvh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                px: 2,
                background: "linear-gradient(160deg, #05223b 0%, #0a3a5f 45%, #0f5c8a 100%)",
            }}
        >
            <Paper
                elevation={6}
                sx={{
                    width: "100%",
                    maxWidth: 980,
                    borderRadius: 3,
                    px: { xs: 2, sm: 5 },
                    py: { xs: 4, sm: 6 },
                    textAlign: "center",
                    background: "rgba(255,255,255,0.94)",
                    backdropFilter: "blur(3px)",
                }}
            >
                <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
                    <Button onClick={() => navigate("/about")}>About</Button>
                </Box>

                <Typography variant="h1" sx={{ fontSize: { xs: "2rem", sm: "2.5rem" }, fontWeight: 700, mb: 1, color: "#0a2f4f" }}>
                    Aviation Safety Search
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ mb: 3, maxWidth: 680, mx: "auto" }}>
                    Retrieval and analysis assistant for NASA ASRS safety reports. Choose your retrieval strategy, optionally enable LLM reasoning, and review explainable ranked results.
                </Typography>

                <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, mb: 2 }}>
                    <Box>
                        <FormControl size="small" fullWidth>
                            <InputLabel id="landing-search-mode-label">Search engine</InputLabel>
                            <Select
                                labelId="landing-search-mode-label"
                                value={searchMode}
                                label="Search engine"
                                onChange={(event) => setSearchMode(event.target.value)}
                            >
                                <MenuItem value="bm25">Quick Search (BM25)</MenuItem>
                                <MenuItem value="embeddings">Concept Search (Embeddings)</MenuItem>
                                <MenuItem value="hybrid">Deeper Search (Hybrid)</MenuItem>
                            </Select>
                        </FormControl>

                        <Box
                            sx={{
                                mt: 1.5,
                                border: "1px solid #dbe5ef",
                                borderRadius: 2,
                                p: 1.25,
                                backgroundColor: "#f8fbff",
                                textAlign: "left",
                            }}
                        >
                            <Typography variant="caption" sx={{ fontWeight: 700, color: "#0a2f4f", display: "block", mb: 0.75 }}>
                                Which mode should I use?
                            </Typography>
                            <Typography variant="caption" sx={{ display: "block", mb: 0.4 }}>
                                <strong>Quick search:</strong> BM25 (fastest, best for exact terms)
                            </Typography>
                            <Typography variant="caption" sx={{ display: "block", mb: 0.4 }}>
                                <strong>Concept search:</strong> Embeddings (finds similar meaning, even with different wording)
                            </Typography>
                            <Typography variant="caption" sx={{ display: "block", mb: 0.4 }}>
                                <strong>Deeper search:</strong> Hybrid (balanced precision + broader coverage)
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                                <strong>LLM Query Enhancement:</strong> helps when your query is short or vague. <strong>LLM Judge:</strong> extra filtering step, usually better precision but slower response.
                            </Typography>
                        </Box>
                    </Box>

                    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", justifyContent: "center", pl: { md: 1 } }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    size="small"
                                    checked={useQe}
                                    onChange={(event) => onToggleQe(event.target.checked)}
                                />
                            }
                            label="LLM Query Enhancement"
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    size="small"
                                    checked={useQeJudge}
                                    onChange={(event) => setUseQeJudge(event.target.checked)}
                                    disabled={!useQe}
                                />
                            }
                            label="LLM Relevance Judge"
                        />
                    </Box>
                </Box>

                <Box sx={{ width: "100%", maxWidth: 760, mx: "auto", mb: 2 }}>
                    <SearchBar onSubmit={onSubmit} />
                </Box>

                <Box sx={{ mt: 1 }}>
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
                    {/* <MetadataFilters /> */}
                </Box>
            </Paper>
        </Box>
    );
};
