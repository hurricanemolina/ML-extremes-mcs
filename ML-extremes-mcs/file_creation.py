import xarray as xr
import numpy as np
import pandas as pd
import calendar
from config import main_path_003, start_year, end_year

class GenerateTrainData:
    
    """Class instantiation of GenerateTrainData:
    
    Here we will be preprocessing data for deep learning model training.
    The objective is to save files for each time index to subsequently load for training.
    IDs are assigned to each file.
    
    Attributes:
        math_path (str): Path where files are located.
        start_year (int): Start year of analysis.
        end_year (int): Final year of analysis.
        variable (str): Variable for file generation. Defaults to ``None``.
        month (int): Month of analysis. Defaults to ``None``.
        instant (boolean): Whether instantaneous variable. Defaults to ``False``, which is the 3-hourly average variable.
        height (int): The respective height index of the file. Defaults to ``None``, which is for single level variables.
        pressure (boolean): Whether to use pressure surfaces variable file. Defaults to ``False`` (e.g., 002 plev files).
        ens_num (str): The CESM CAM ensemble number. Defaults to ``003``.
    """
        
    def __init__(self, main_path, start_year, end_year, variable=None, month=None, instant=False, height=None, pressure=False, ens_num='003'):
        
        self.main_directory = main_path
        self.year_start = start_year
        self.year_end = end_year
        self.variable = variable
        self.month = month
        self.instant = instant
        if self.instant:
            self.inst_str = 'h4'
        if not self.instant:
            self.inst_str = 'h3'
        self.height = height
        self.pressure = pressure
        self.ens_num = ens_num
        
    def make_month(self):
        """
        Returns all caps month string.
        """
        return calendar.month_abbr[self.month].upper()
    
    def make_dict(self, start_str=f'01-01-2000 03:00:00', end_str=f'01-01-2006 00:00:00'):
        """
        Create dictionary of the indices using study time range.
        These indices must be fixed values for the study time range.
        For 002 use: start_str=f'04-01-1991', end_str=f'07-31-2005 23:00:00'
        """
        alldates = pd.date_range(start=start_str, end=end_str, freq='3H')
        dict_dates = {}
        for i, j in enumerate(alldates):
            dict_dates[j] = i
        return dict_dates
        
    def make_years(self):
        """
        Returns array of years for data generation.
        """
        years = pd.date_range(start=self.year_start+'-01-01', end=self.year_end+'-01-01', freq='AS-JAN').year
        return years
    
    def open_variable_file(self, year):
        """
        Returns opened and sliced spatial region of data for respective year.
        """
        if self.ens_num == '002':
            if self.pressure:
                data = xr.open_dataset(
                    f'{self.main_directory}/plevs_FV_768x1152.bilinear.{self.make_month()}_b.e13.B20TRC5CN.ne120_g16.002_{self.variable}_{year}.nc')
                data = data.assign_coords(ncl4=("ncl4",data.time),
                                          ncl6=("ncl6",data.lat.values),
                                          ncl7=("ncl7",data.lon.values))
        if self.ens_num == '003':
            data = xr.open_dataset(
                f'{self.main_directory}/b.e13.B20TRC5CN.ne120_g16.003.cam.{self.inst_str}.{self.variable}.{year}010100Z-{year}123121Z.regrid.23x0.31.nc')
        return data
    
    def open_mask_file(self, year=None):
        """
        Open the MCS mask file.
        """
        if self.ens_num == '002':
            mask = xr.open_dataset(f"{self.main_directory}/mask_camPD_{self.make_month()}.nc")
        if self.ens_num == '003':
            mask = xr.open_dataset(f"{self.main_directory}/mask_camPD_{year}.nc")
        return mask
    
    def slice_grid(self, data_mask, data, lat='lat', lon='lon'):
        """
        Slice the variable data on pressure level grid to match the mask data.

        Args:
            mask (xarray dataset): MCS object mask.
            data (xarray dataset): The data to slice.
            lat (str): Latitude dimension name. Defaults to ``lat``.
            lon (str): Longitude dimension name. Defaults to ``lon``.

        Returns:
            Variable data sliced to spatial extent of the mask data.
        """
        datavar = data[self.variable]
        if self.ens_num == '002':
            datavar = datavar.isel(ncl5=self.height,
                                   ncl6=slice(np.where(data[lat].values==data_mask['lat'][0].values)[0][0],
                                              np.where(data[lat].values==data_mask['lat'][-1].values)[0][0]+1),
                                   ncl7=slice(np.where(data[lon].values==data_mask['lon'][0].values)[0][0],
                                              np.where(data[lon].values==data_mask['lon'][-1].values)[0][0]+1))
        if self.ens_num == '003':
            datavar = datavar.isel(lat=slice(np.where(data[lat].values==data_mask['lat'][0].values)[0][0],
                                             np.where(data[lat].values==data_mask['lat'][-1].values)[0][0]+1),
                                   lon=slice(np.where(data[lon].values==data_mask['lon'][0].values)[0][0],
                                             np.where(data[lon].values==data_mask['lon'][-1].values)[0][0]+1))
        return datavar

    def generate_files(self):
        """
        Save the files for each time period and variable with respective ID.
        """
        print("starting file generation...")
        yr_array = self.make_years()
        indx_array = self.make_dict()
        print("opening variable file...")
        for yr in yr_array:
            data = self.open_variable_file(yr)
            if self.ens_num == '002':
                if self.pressure:
                    mask = self.open_mask_file()
                    data = self.slice_grid(mask, data)
                    print(f"{yr} opened and sliced successfully...")
                    for t in data.ncl4:
                        tmpdata = data.sel(ncl4=t)
                        tmpdata = tmpdata.to_dataset()
                        indx_val = indx_array[pd.to_datetime(t.astype('str').values)]
                        tmpdata.to_netcdf(
                            f"{self.main_directory}/dl_files/plev_{self.variable}_hgt{self.height}_ID{indx_val}.nc")
            if self.ens_num == '003':
                mask = self.open_mask_file(yr)
                data = self.slice_grid(mask, data)
                print(f"{yr} opened and sliced successfully...")
                for t in data.time:
                    tmpdata = data.sel(time=t)
                    tmpdata = tmpdata.to_dataset()
                    indx_val = indx_array[pd.to_datetime(t.astype('str').values)]
                    tmpdata.to_netcdf(
                        f"{self.main_directory}/dl_files/file003_{self.inst_str}_{self.variable}_ID{indx_val}.nc")
        print("Job complete!")
        
    def generate_masks(self):
        """
        Save the files for each time period and mask with respective ID.
        """
        print("starting mask file generation...")
        yr_array = self.make_years()
        indx_array = self.make_dict()
        
        if self.ens_num == '002':
            print('Training options not yet available for member 002')
            return
        
        if self.ens_num == '003':
            for yr in yr_array:
                mask = self.open_mask_file(yr)
                for t in mask.time:
                    tmpmask = mask.sel(time=t)
                    indx_val = indx_array[pd.to_datetime(t.astype('str').values)]
                    tmpmask.to_netcdf(f"{self.main_directory}/dl_files/mask_ID{indx_val}.nc")
        print("Job complete!")
