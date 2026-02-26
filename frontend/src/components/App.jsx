import { React } from "react";
import "../styles/style.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Search, Results, About } from "./pages";

export const App = () => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Search />} />
                <Route path="/results" element={<Results />} />
                <Route path="/about" element={<About />} />
            </Routes>
        </BrowserRouter>
    );
};