import { Box, Typography } from "@mui/material";
import { MetadataFilters, SearchBar } from "../common";
import { useNavigate } from "react-router-dom";

export const Search = () => {
    const navigate = useNavigate();
    
    const onSubmit = (query) => {
        navigate("/results");
    }

    return <>
        <Box
            sx={{
                height: '100dvh', 
                // backgroundColor: '#f8f9fa',
                position: 'relative'
            }}
        >
            <Box sx={{ 
                display: 'flex', 
                flexDirection: "column",
                alignItems: 'center', 
                justifyContent: 'center',
                textAlign: "center",
                py: "30dvh",
                mb: 1
            }}>
                {/* Title */}
                <Box>
                    <Typography 
                        variant = "h1"
                        sx = {{
                            fontSize: "30pt"
                        }}
                    >
                        Aviation Safety Search
                    </Typography>
                </Box>
                {/* Search Bar */}
                <Box
                    sx = {{
                        py: "1dvh",
                        width: "40dvw"
                    }}
                >
                    <SearchBar
                        onSubmit={onSubmit}
                    />
                </Box>
                {/* Filters Button */}
                <Box>
                    <MetadataFilters/>
                </Box>
            </Box>
        </Box>
    </>
}