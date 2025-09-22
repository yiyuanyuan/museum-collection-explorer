import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

export const fetchOccurrences = async (filters = {}, page = 0, pageSize = 300000) => {
  try {
    const params = {
      page,
      pageSize,  // Now defaults to 300000 to get all records
      ...filters
    };

    const response = await axios.get(`${API_BASE_URL}/occurrences`, { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching occurrences:', error);
    throw error;
  }
};

export const fetchStatistics = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/statistics`);
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

    const response = await axios.get(`${API_BASE_URL}/occurrences`, { params });
    return response.data;
  } catch (error) {
    console.error('Error searching by location:', error);
    throw error;
  }
};