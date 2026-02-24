import { useEffect, useState } from "react";
import { Box, Button, InputAdornment, TextField } from "@mui/material";
import { Search as SearchIcon } from "@mui/icons-material";

export const SearchBar = ({ disabled, onSubmit, initQuery }) => {
    const [userQuery, setUserQuery] = useState("");

    const handleSubmit = () => {
        localStorage.setItem("user-query", userQuery);
        onSubmit();
    };

    const onEnter = (event) => {
        if (event.key === "Enter") {
            handleSubmit();
        }
    };

    useEffect(() => {
        if (initQuery) {
            setUserQuery(initQuery);
        }
    }, [initQuery]);

    return <Box sx={{ display: "flex", gap: 1, alignItems: "stretch", width: "100%" }}>
        <TextField
            sx={{ 
                flex: 1,
                backgroundColor: 'white'
            }}
            id="searchTerm"
            placeholder="Search ASRS..."
            variant="outlined"
            value={userQuery}
            onChange={event => { setUserQuery(event.target.value) }}
            onKeyDown={onEnter}
            disabled={disabled}
            InputProps={{
                startAdornment: (
                    <InputAdornment position="start">
                        <SearchIcon color="action" />
                    </InputAdornment>
                ),
            }}
        />
        <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={disabled}
            sx={{ minWidth: 100 }}
        >
            Search
        </Button>
    </Box>
}