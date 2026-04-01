import axios from "axios";

const apiClient = axios.create({
  baseURL: "",
  timeout: 60000,
});

export default apiClient;
