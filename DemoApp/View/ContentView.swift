//
//  ContentView.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import SwiftUI

struct ContentView: View {

    @StateObject var viewmodel = UserProfileViewModel()

    var body: some View {

        NavigationView {
            List(viewmodel.userProfileList) { model in
                VStack(alignment: .leading) {
                    Text("\(Constants.name) \(model.name)")
                        .overlay {
                            NavigationLink(
                                destination: {
                                    DetailView(userModel: model)
                                        .environmentObject(viewmodel)
                                },
                                label: {
                                    Text(Constants.userDetail)
                                }
                            )
                            .opacity(0)
                        }
                        .font(.headline)
                        .fontWeight(.heavy)

                    Text("\(Constants.companyName) \(model.company?.name ?? String.empty)")
                        .font(.headline)
                }
                .padding(10)
            }
            .navigationTitle(Constants.userList)
        }
        .onAppear {
            viewmodel.trigger(by: .getUserData)
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
