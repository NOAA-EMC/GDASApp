import netCDF4 as nc
import numpy as np
import time


def nc_merge(file_name1, file_name2, target_name):
    ncf1 = nc.Dataset(file_name1)
    ncf2 = nc.Dataset(file_name2)
    ncf = nc.Dataset(target_name, "w", format="NETCDF4")

    # Add attr for dataset
    ncf1_attr = ncf1.__dict__
    ncf2_attr = ncf2.__dict__
    ncf_attr = {}
    for k, v1 in ncf1_attr.items():
        ncf_attr[k] = v1
        v2 = ncf2_attr.get(k)
        if v2 and v1 != v2:
            ncf_attr[k] = f"1: {v1}, 2: {v2}"
    ncf.setncatts(ncf_attr)

    # Create groups
    for grp in ncf1.groups:
        print(grp)
        ncf.createGroup(grp)

    # Create dimensions
    ncf1_dims = ncf1.dimensions
    ncf2_dims = ncf2.dimensions
    for dim_key in ncf1_dims:
        dim1 = ncf1_dims[dim_key]
        dim2 = ncf2_dims.get(dim_key)
        if dim2:
            if dim1.name == 'Location':
                dim_size = dim1.size + dim2.size
            else:
                dim_size = dim1.size
            ncf.createDimension(dim1.name, dim_size)
        else:
            print('error: dimension mismatch')  # TODO throw an exception

    # Create Dimension variables
    vars2 = ncf2.variables
    for var1 in ncf1.variables.values():
        if var1.name == 'Channel':
            var = var1
        else:
            var = np.concatenate((var1, vars2[var1.name]))
        ncf_var = ncf.createVariable(var1.name, var1.datatype, var1.dimensions)
        ncf_var[:] = var[:]
        attrs = var1.ncattrs()
        for attr in attrs:
            ncf_var.setncattr(attr, var1.getncattr(attr))

    # Create Group variables
    grp1 = ncf1.groups
    grp2 = ncf2.groups
    for k in grp1.keys():
        vars1 = grp1[k].variables
        vars2 = grp2[k].variables
        for key in vars1:
            var = vars1[key]
            if vars2.get(key):
                var2 = vars2[key]
            else:
                print(f"-----------Warning: {key} is not existed in ncf2, skip -----------------")
                continue
            var_array = np.concatenate((var, var2))
            var_path = f"{grp1[k].path}/{var.name}"
            var_fill_value = var.getncattr('_FillValue')
            ncf_var = ncf.createVariable(var_path, var.datatype, var.dimensions, fill_value=var_fill_value)
            ncf_var[:] = var_array[:]
            attrs = var.ncattrs()
            for attr in attrs:
                if attr != '_FillValue':
                    ncf_var.setncattr(attr, var.getncattr(attr))


def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.6f} seconds to execute.")
        return result
    return wrapper
