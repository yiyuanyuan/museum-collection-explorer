import axios from 'axios';

// Make sure the URL includes /api at the end
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://museum-collection-explorer-api.onrender.com';

export const fetchOccurrences = async (filters = {}, page = 0, pageSize = 500) => {
  try {
    const params = {
      page,
      pageSize,
      ...filters
    };

    // Add /api to the endpoint path
    const response = await axios.get(`${API_BASE_URL}/api/occurrences`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching occurrences:', error);
    throw error;
  }
};

export const fetchStatistics = async () => {
  try {
    // Add /api to the endpoint path
    const response = await axios.get(`${API_BASE_URL}/api/statistics`);
    return response.data;
  } catch (error) {
    console.error('Error fetching statistics:', error);
    throw error;
  }
};

export const searchByLocation = async (lat, lon, radius = 10) => {
  try {
    const params = {
      lat,
      lon,
      radius
    };

    // Add /api to the endpoint path
    const response = await axios.get(`${API_BASE_URL}/api/occurrences`, { params });
    return response.data;
  } catch (error) {
    console.error('Error searching by location:', error);
    throw error;
  }
};