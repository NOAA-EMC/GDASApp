#include <iostream>
#include <vector>
#include <mpi.h>

#include "eckit/mpi/Comm.h"
#include "oops/mpi/mpi.h"

int main(int argc, char** argv) {

  //MPI_Init(&argc, &argv);
    const eckit::mpi::Comm & comm = oops::mpi::world();

    std::cout << comm.size() << std::endl << comm.rank() << std::endl;
    /*
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // Create a local vector for each process
    std::vector<int> localVector;
    for (int i = 0; i < 10000; i++) {
        localVector.push_back(rank * 5 + i);
    }

    // Determine the size of the local vectors
    int localSize = localVector.size();

    // Determine the total size of all local vectors
    int totalSize;
    MPI_Allreduce(&localSize, &totalSize, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);

    // Create a buffer to store the concatenated vectors
    std::vector<int> concatenatedVector(totalSize);

    // Gather all local vectors into the concatenated vector
    MPI_Allgather(
        localVector.data(),    // Pointer to the local vector's data
        localSize,             // Size of the local vector
        MPI_INT,               // Type of data in the local vector
        concatenatedVector.data(), // Pointer to the concatenated vector
        localSize,             // Size of each local vector
        MPI_INT,               // Type of data in the concatenated vector
        MPI_COMM_WORLD
    );

    // Print the concatenated vector
    if (rank == 0) {
        std::cout << "Concatenated Vector: ";
        for (int i = 0; i < totalSize; i++) {
            std::cout << concatenatedVector[i] << " ";
        }
        std::cout << std::endl;
    }
    */
    MPI_Finalize();
    return 0;
}
